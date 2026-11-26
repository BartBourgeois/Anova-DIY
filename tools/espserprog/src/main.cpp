// espserprog: flashrom's serprog protocol on a classic ESP32, for reading SPI NOR flash only (J-211).
//
// flashrom on the PC talks to it as `-p serprog:dev=COM<n>:921600`. Two things make it safer than a generic reader:
// - Read-only in the firmware: an SPI operation whose first byte is a write enable, a program, an erase or a status
//   register write is refused with NAK before anything reaches the chip. Without write enable an SPI NOR flash
//   ignores every program and erase command, so refusing 0x06 and 0x50 alone would do; the others are refused too.
//   The esp32-rw build (SERPROG_ALLOW_WRITE, the loose practice chip only, J-213) leaves the guard out.
// - Hi-Z until asked: the four SPI pins are inputs (not driven) from power-up until flashrom enables the pin drivers
//   (S_PIN_STATE 1), and inputs again when it disables them (S_PIN_STATE 0, sent at the end of a session) or when an
//   operation hasn't come for 2 s. So the reader never drives an unpowered board's lines while idle.
// Pins (the ESP32's VSPI): GPIO5 CS, GPIO18 SCK, GPIO23 MOSI (to the flash's DI), GPIO19 MISO (from DO). GPIO2 (the
// devkit's blue LED) is on while the drivers are on. The protocol: flashrom's Documentation/serprog/serprog-protocol.
//
// Live view (J-214): built with WIFI_SSID and WIFI_PASS (from the environment at build time, never from a file in
// the repository), the ESP32 joins that network as `espserprog` and serves a view-only status page on port 80
// (http://espserprog.local/): the session, the current operation and address, progress, throughput, totals, the
// chip's ID and the last operations. The web server runs on core 0; serprog stays on core 1 and only updates counters.
// The page has no controls. Built without them, there is no Wi-Fi at all.

#include <Arduino.h>
#include <ESPmDNS.h>
#include <SPI.h>
#include <WebServer.h>
#include <WiFi.h>

#ifndef SERPROG_BAUD
#define SERPROG_BAUD 921600
#endif
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASS
#define WIFI_PASS ""
#endif
#ifdef SERPROG_ALLOW_WRITE
static const char *VARIANT = "espserprog-rw";
#else
static const char *VARIANT = "espserprog-ro";
#endif

static const int PIN_CS = 5, PIN_SCK = 18, PIN_MISO = 19, PIN_MOSI = 23, PIN_LED = 2;
static const uint8_t ACK = 0x06, NAK = 0x15;
static const uint32_t MAX_SEND = 512;   // largest slen accepted (a read needs 4-5 bytes, a page program 260)
static const uint32_t MAX_READ = 65536; // reported to flashrom as the largest rlen per operation
static const uint32_t IDLE_MS = 2000;   // drivers off after this long without an operation

enum : uint8_t {
  S_NOP = 0x00, Q_IFACE = 0x01, Q_CMDMAP = 0x02, Q_PGMNAME = 0x03, Q_SERBUF = 0x04, Q_BUSTYPE = 0x05,
  Q_WRNMAXLEN = 0x08, SYNCNOP = 0x10, Q_RDNMAXLEN = 0x11, S_BUSTYPE = 0x12, O_SPIOP = 0x13, S_SPI_FREQ = 0x14,
  S_PIN_STATE = 0x15,
  Q_NETINFO = 0xF0,  // espserprog's own: ACK + IPv4 (4 bytes) + Wi-Fi status (255 = built without Wi-Fi)
};
static const uint8_t SUPPORTED[] = {S_NOP, Q_IFACE, Q_CMDMAP, Q_PGMNAME, Q_SERBUF, Q_BUSTYPE, Q_WRNMAXLEN,
                                    SYNCNOP, Q_RDNMAXLEN, S_BUSTYPE, O_SPIOP, S_SPI_FREQ, S_PIN_STATE};

// SPI NOR opcodes that write or prepare a write: write enable (0x06, 0x50 volatile), page/quad program
// (0x02, 0x32, 0x38, 0x12, 0x34, 0x3E), erases (0x20, 0x21, 0x52, 0xD8, 0xDC, 0xC7, 0x60, 0x44), status register writes
// (0x01, 0x31, 0x11), security/OTP register program (0x42, 0xB1), lock bits (0x36, 0x39, 0x7E, 0x98, 0xA6),
// suspend/resume and reset (0x75, 0x7A, 0xB0, 0x30, 0x66, 0x99).
static const uint8_t REFUSED[] = {0x06, 0x50, 0x02, 0x32, 0x38, 0x12, 0x34, 0x3E, 0x20, 0x21, 0x52, 0xD8, 0xDC,
                                  0xC7, 0x60, 0x44, 0x01, 0x31, 0x11, 0x42, 0xB1, 0x36, 0x39, 0x7E, 0x98, 0xA6,
                                  0x75, 0x7A, 0xB0, 0x30, 0x66, 0x99};
// opcodes followed by a 3-byte address, for the live view
static const uint8_t ADDRESSED[] = {0x03, 0x0B, 0x02, 0x20, 0x52, 0xD8, 0x5A, 0x32, 0x42, 0x44, 0x48};

static SPIClass spi(VSPI);
static uint32_t freq = 2000000;
static bool driving = false;
static uint32_t lastOp = 0;
static uint8_t sendBuf[MAX_SEND], readBuf[1024], zeros[1024];

// ---- live-view counters: written on core 1 (serprog), read on core 0 (web) ----
struct OpLog { uint32_t ms, addr, slen, rlen; uint8_t opcode, refused; };
static const int LOG_N = 32;
static portMUX_TYPE statMux = portMUX_INITIALIZER_UNLOCKED;
static struct {
  uint32_t ops, refusedOps, bytesRead, bytesWritten, sessions;
  uint32_t sessionStart, sessionEnd, sessionRead, sessionWritten, sessionOps;
  uint32_t curOpcode, curAddr, curLen, curStart;  // the operation in progress (curStart 0 = none)
  uint32_t maxReadEnd;                             // highest address read to in this session
  uint32_t jedec;                                  // last RDID answer, 3 bytes
  uint32_t reReads, readFailures;                  // verified reads: blocks read again, operations refused
  bool session;
  OpLog log[LOG_N];
  int logHead;
} st;

static bool inList(uint8_t v, const uint8_t *list, size_t n) {
  for (size_t i = 0; i < n; i++)
    if (list[i] == v) return true;
  return false;
}

static void logOp(uint8_t opcode, uint32_t addr, uint32_t slen, uint32_t rlen, bool refusedOp) {
  portENTER_CRITICAL(&statMux);
  OpLog &e = st.log[st.logHead];
  e = {millis(), addr, slen, rlen, opcode, (uint8_t)refusedOp};
  st.logHead = (st.logHead + 1) % LOG_N;
  st.ops++;
  st.sessionOps++;
  if (refusedOp) st.refusedOps++;
  portEXIT_CRITICAL(&statMux);
}

static void pinsOff() {
  if (driving) spi.end();
  for (int p : {PIN_CS, PIN_SCK, PIN_MISO, PIN_MOSI}) pinMode(p, INPUT);
  digitalWrite(PIN_LED, LOW);
  if (driving) {
    st.session = false;
    st.sessionEnd = millis();
  }
  driving = false;
}

static void pinsOn() {
  if (driving) return;
  pinMode(PIN_CS, OUTPUT);
  digitalWrite(PIN_CS, HIGH);
  spi.begin(PIN_SCK, PIN_MISO, PIN_MOSI, -1);
  digitalWrite(PIN_LED, HIGH);
  driving = true;
  portENTER_CRITICAL(&statMux);
  st.session = true;
  st.sessions++;
  st.sessionStart = millis();
  st.sessionEnd = 0;
  st.sessionRead = st.sessionWritten = st.sessionOps = st.maxReadEnd = 0;
  portEXIT_CRITICAL(&statMux);
}

static bool readN(uint8_t *dst, size_t n) { return Serial.readBytes(dst, n) == n; }

static uint32_t read24() {
  uint8_t b[3] = {0, 0, 0};
  readN(b, 3);
  return b[0] | (b[1] << 8) | ((uint32_t)b[2] << 16);
}

static void send24(uint32_t v) {
  uint8_t b[3] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16)};
  Serial.write(b, 3);
}

static bool refused(uint8_t opcode) {
#ifdef SERPROG_ALLOW_WRITE  // the esp32-rw build, for the loose practice chip only (J-213)
  (void)opcode;
  return false;
#else
  return inList(opcode, REFUSED, sizeof(REFUSED));
#endif
}

// A plain read (0x03), verified in the reader: each block of up to BLOCK bytes is read from the chip twice, each time
// with its own command and address; if the two differ, again (up to TRIES reads) until two agree. The ESP32's SPI
// unit moves data in 64-byte units and shares its registers between the bytes sent and received, so a unit that
// didn't complete returns the dummy bytes sent (0x00): seen once as 64 zero bytes at 0x0FAE00 on 2026-11-06 (J-214).
// SPI at 2 MHz is about 2.7 times faster than the 921 600-baud link, so the second read costs no time overall.
static const uint32_t BLOCK = 1024;
static const int TRIES = 6;
static uint8_t *opBuf;  // MAX_READ bytes from the heap (setup): too big for the static RAM area
static uint8_t tryBuf[2][BLOCK];

static void readBlock(uint32_t addr, uint8_t *dst, uint32_t n) {
  uint8_t cmd[4] = {0x03, (uint8_t)(addr >> 16), (uint8_t)(addr >> 8), (uint8_t)addr};
  spi.beginTransaction(SPISettings(freq, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_CS, LOW);
  spi.writeBytes(cmd, 4);
  spi.transferBytes(zeros, dst, n);
  digitalWrite(PIN_CS, HIGH);
  spi.endTransaction();
}

static bool verifiedRead(uint32_t addr, uint32_t rlen) {
  for (uint32_t off = 0; off < rlen; off += BLOCK) {
    uint32_t n = rlen - off < BLOCK ? rlen - off : BLOCK;
    uint32_t a = (addr + off) & 0xFFFFFF;
    readBlock(a, opBuf + off, n);
    bool agreed = false;
    for (int t = 1; t < TRIES && !agreed; t++) {
      uint8_t *other = tryBuf[t & 1];
      readBlock(a, other, n);
      if (memcmp(opBuf + off, other, n) == 0) {
        agreed = true;
      } else {
        st.reReads++;
        if (t >= 2 && memcmp(tryBuf[(t + 1) & 1], other, n) == 0) {  // the last two agree: take them
          memcpy(opBuf + off, other, n);
          agreed = true;
        }
      }
    }
    if (!agreed) return false;
  }
  return true;
}

static void spiOp() {
  uint32_t slen = read24(), rlen = read24();
  if (slen > MAX_SEND || rlen > (1u << 24)) {  // drain what we can't hold, then refuse
    for (uint32_t i = 0; i < slen; i++) Serial.read();
    Serial.write(NAK);
    return;
  }
  if (!readN(sendBuf, slen)) {
    Serial.write(NAK);
    return;
  }
  uint8_t opcode = slen ? sendBuf[0] : 0;
  uint32_t addr = (slen >= 4 && inList(opcode, ADDRESSED, sizeof(ADDRESSED)))
                      ? ((uint32_t)sendBuf[1] << 16) | (sendBuf[2] << 8) | sendBuf[3] : 0xFFFFFFFF;
  if (slen && refused(opcode)) {
    logOp(opcode, addr, slen, rlen, true);
    Serial.write(NAK);
    return;
  }
  pinsOn();
  lastOp = millis();
  st.curOpcode = opcode;
  st.curAddr = addr;
  st.curLen = rlen;
  st.curStart = lastOp | 1;
  if (opcode == 0x03 && slen == 4 && rlen <= MAX_READ && opBuf) {  // a plain read: every block read twice, J-214
    bool ok = verifiedRead(addr, rlen);
    st.curStart = 0;
    logOp(opcode, addr, slen, rlen, false);
    lastOp = millis();
    if (!ok) {
      st.readFailures++;
      Serial.write(NAK);  // no two reads of a block agreed: refuse the operation, flashrom stops
      return;
    }
    Serial.write(ACK);
    Serial.write(opBuf, rlen);
    st.bytesRead += rlen;
    st.sessionRead += rlen;
    if (addr + rlen > st.maxReadEnd) st.maxReadEnd = addr + rlen;
    return;
  }
  Serial.write(ACK);
  spi.beginTransaction(SPISettings(freq, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_CS, LOW);
  if (slen) spi.writeBytes(sendBuf, slen);
  uint32_t left = rlen;
  bool first = true;
  while (left) {
    uint32_t n = left > sizeof(readBuf) ? sizeof(readBuf) : left;
    spi.transferBytes(zeros, readBuf, n);
    if (first && opcode == 0x9F && n >= 3) st.jedec = (readBuf[0] << 16) | (readBuf[1] << 8) | readBuf[2];
    first = false;
    Serial.write(readBuf, n);
    left -= n;
    st.bytesRead += n;
    st.sessionRead += n;
    if (addr != 0xFFFFFFFF && addr + (rlen - left) > st.maxReadEnd) st.maxReadEnd = addr + (rlen - left);
  }
  digitalWrite(PIN_CS, HIGH);
  spi.endTransaction();
  if (opcode == 0x02 && slen > 4) {
    st.bytesWritten += slen - 4;
    st.sessionWritten += slen - 4;
  }
  st.curStart = 0;
  logOp(opcode, addr, slen, rlen, false);
  lastOp = millis();
}

// ---- the live view (core 0) ----
static WebServer web(80);
static bool wifiWanted() { return WIFI_SSID[0] != 0; }

static const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>espserprog live</title><style>
:root{--bg:#1e1e1e;--panel:#2a2a2a;--text:#f2f2f2;--dim:#a8a8a8;--ok:#3ddc5a;--warn:#ff8c00;--bad:#ff4040;--acc:#2f9bff}
body{margin:0;padding:16px;background:var(--bg);color:var(--text);font:15px system-ui,Segoe UI,Arial,sans-serif}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--dim);margin-bottom:14px}.grid{display:grid;gap:10px;
grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}.card{background:var(--panel);border-radius:10px;padding:10px 12px}
.k{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.v{font-size:20px;font-weight:600;
font-variant-numeric:tabular-nums;word-break:break-all}.bar{height:14px;background:#111;border-radius:7px;overflow:hidden;margin-top:6px}
.fill{height:100%;background:var(--acc);width:0}table{width:100%;border-collapse:collapse;margin-top:14px;font-size:13px;
font-variant-numeric:tabular-nums}td,th{padding:4px 6px;border-bottom:1px solid #333;text-align:left}th{color:var(--dim);font-weight:500}
.ro{color:var(--ok)}.rw{color:var(--warn)}.no{color:var(--bad);font-weight:600}</style></head><body>
<h1>espserprog <span id="variant"></span></h1><div class="sub">Live, view only. Updates every 0.3 s. <span id="net"></span></div>
<div class="grid">
<div class="card"><div class="k">Session</div><div class="v" id="session">-</div></div>
<div class="card"><div class="k">Now</div><div class="v" id="now">-</div></div>
<div class="card"><div class="k">Address</div><div class="v" id="addr">-</div></div>
<div class="card"><div class="k">Throughput</div><div class="v" id="rate">-</div></div>
<div class="card" style="grid-column:1/-1"><div class="k">Read progress (highest address read / chip size)</div>
<div class="v" id="prog">-</div><div class="bar"><div class="fill" id="fill"></div></div></div>
<div class="card"><div class="k">Chip (RDID)</div><div class="v" id="chip">-</div></div>
<div class="card"><div class="k">SPI clock</div><div class="v" id="freq">-</div></div>
<div class="card"><div class="k">Read, this session / total</div><div class="v" id="read">-</div></div>
<div class="card"><div class="k">Written, this session / total</div><div class="v" id="written">-</div></div>
<div class="card"><div class="k">Operations / refused</div><div class="v" id="ops">-</div></div>
<div class="card"><div class="k">Blocks re-read / reads failed</div><div class="v" id="rr">-</div></div>
</div>
<table><thead><tr><th>t (s)</th><th>op</th><th>name</th><th>address</th><th>sent</th><th>read</th><th></th></tr></thead><tbody id="log"></tbody></table>
<script>
const N={0x03:"READ",0x0B:"FAST_READ",0x9F:"RDID",0x90:"REMS",0xAB:"RES",0x05:"RDSR",0x35:"RDSR2",0x15:"RDSR3",
0x5A:"SFDP",0x4B:"RDUID",0x06:"WREN",0x04:"WRDI",0x50:"EWSR",0x02:"PAGE_PROG",0x20:"ERASE_4K",0x52:"ERASE_32K",
0xD8:"ERASE_64K",0xC7:"CHIP_ERASE",0x60:"CHIP_ERASE",0x01:"WRSR",0x31:"WRSR2",0x11:"WRSR3",0xB9:"POWER_DOWN",0x66:"RST_EN",0x99:"RESET"};
const V={0xEF:"Winbond",0x20:"XMC / Micron",0xC2:"Macronix",0xC8:"GigaDevice",0x9D:"ISSI",0x01:"Spansion"};
const h=(v,w)=>"0x"+v.toString(16).toUpperCase().padStart(w,"0"),$=id=>document.getElementById(id);
const sz=b=>b>=1048576?(b/1048576).toFixed(2)+" MiB":b>=1024?(b/1024).toFixed(1)+" KiB":b+" B";
async function tick(){try{const s=await(await fetch("/status")).json();
$("variant").textContent=s.variant;$("variant").className=s.variant.endsWith("-ro")?"ro":"rw";
$("net").textContent="RSSI "+s.rssi+" dBm, up "+Math.round(s.uptime/1000)+" s";
const dur=((s.session?s.now:s.sessionEnd)-s.sessionStart)/1000;
$("session").textContent=s.session?"ACTIVE, "+dur.toFixed(1)+" s":(s.sessions?"idle (last "+dur.toFixed(1)+" s)":"idle");
$("now").textContent=s.busy?(N[s.op]||h(s.op,2))+" "+sz(s.len):"-";
$("addr").textContent=s.busy&&s.addr!==4294967295?h(s.addr,6):"-";
$("rate").textContent=dur>0?sz(Math.round(s.sessionRead/dur))+"/s":"-";
const id=s.jedec,cap=id&0xFF,size=cap>=0x10&&cap<=0x20?2**cap:0;
$("chip").textContent=id?h(id,6)+" "+(V[id>>16]||"?")+(size?" "+sz(size):""):"-";
const p=size?Math.min(100,100*s.maxReadEnd/size):0;$("prog").textContent=size?h(s.maxReadEnd,6)+" / "+h(size,6)+"  "+p.toFixed(1)+" %":"-";
$("fill").style.width=p+"%";$("freq").textContent=(s.freq/1e6).toFixed(2)+" MHz";
$("read").textContent=sz(s.sessionRead)+" / "+sz(s.bytesRead);$("written").textContent=sz(s.sessionWritten)+" / "+sz(s.bytesWritten);
$("ops").innerHTML=s.ops+" / "+(s.refused?'<span class="no">'+s.refused+"</span>":"0");
$("rr").innerHTML=(s.reReads?'<span class="rw">'+s.reReads+"</span>":"0")+" / "+(s.readFailures?'<span class="no">'+s.readFailures+"</span>":"0");
$("log").innerHTML=s.log.map(e=>"<tr><td>"+(e.ms/1000).toFixed(2)+"</td><td>"+h(e.op,2)+"</td><td>"+(N[e.op]||"")+"</td><td>"+
(e.addr===4294967295?"":h(e.addr,6))+"</td><td>"+e.slen+"</td><td>"+e.rlen+"</td><td>"+(e.refused?'<span class="no">REFUSED</span>':"")+"</td></tr>").join("")}
catch(e){$("net").textContent="no connection"}}setInterval(tick,300);tick();
</script></body></html>)HTML";

static void handleStatus() {
  static char buf[4096];
  OpLog copy[LOG_N];
  int head;
  portENTER_CRITICAL(&statMux);
  memcpy(copy, st.log, sizeof(copy));
  head = st.logHead;
  portEXIT_CRITICAL(&statMux);
  int n = snprintf(buf, sizeof(buf),
                   "{\"variant\":\"%s\",\"now\":%lu,\"uptime\":%lu,\"rssi\":%d,\"session\":%s,\"sessions\":%lu,"
                   "\"sessionStart\":%lu,\"sessionEnd\":%lu,\"busy\":%s,\"op\":%lu,\"addr\":%lu,\"len\":%lu,"
                   "\"maxReadEnd\":%lu,\"jedec\":%lu,\"freq\":%lu,\"sessionRead\":%lu,\"bytesRead\":%lu,"
                   "\"sessionWritten\":%lu,\"bytesWritten\":%lu,\"ops\":%lu,\"refused\":%lu,\"reReads\":%lu,"
                   "\"readFailures\":%lu,\"log\":[",
                   VARIANT, (unsigned long)millis(), (unsigned long)millis(), WiFi.RSSI(), st.session ? "true" : "false",
                   (unsigned long)st.sessions, (unsigned long)st.sessionStart, (unsigned long)st.sessionEnd,
                   st.curStart ? "true" : "false", (unsigned long)st.curOpcode, (unsigned long)st.curAddr,
                   (unsigned long)st.curLen, (unsigned long)st.maxReadEnd, (unsigned long)st.jedec, (unsigned long)freq,
                   (unsigned long)st.sessionRead, (unsigned long)st.bytesRead, (unsigned long)st.sessionWritten,
                   (unsigned long)st.bytesWritten, (unsigned long)st.ops, (unsigned long)st.refusedOps,
                   (unsigned long)st.reReads, (unsigned long)st.readFailures);
  bool firstEntry = true;
  for (int i = 0; i < LOG_N && n < (int)sizeof(buf) - 160; i++) {  // newest first
    const OpLog &e = copy[(head - 1 - i + LOG_N) % LOG_N];
    if (!e.ms) continue;
    n += snprintf(buf + n, sizeof(buf) - n, "%s{\"ms\":%lu,\"op\":%u,\"addr\":%lu,\"slen\":%lu,\"rlen\":%lu,\"refused\":%u}",
                  firstEntry ? "" : ",", (unsigned long)e.ms, e.opcode, (unsigned long)e.addr, (unsigned long)e.slen,
                  (unsigned long)e.rlen, e.refused);
    firstEntry = false;
  }
  snprintf(buf + n, sizeof(buf) - n, "]}");
  web.sendHeader("Cache-Control", "no-store");
  web.send(200, "application/json", buf);
}

static void webTask(void *) {
  WiFi.persistent(false);  // no Wi-Fi settings written to the ESP32's flash: such writes pause both cores (J-216)
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("espserprog");
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) vTaskDelay(pdMS_TO_TICKS(250));
  MDNS.begin("espserprog");
  MDNS.addService("http", "tcp", 80);
  web.on("/", [] { web.send_P(200, "text/html", PAGE); });
  web.on("/status", handleStatus);
  web.onNotFound([] { web.send(404, "text/plain", "view only"); });
  web.begin();
  for (;;) {
    web.handleClient();
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinsOff();
  opBuf = (uint8_t *)malloc(MAX_READ);  // without it, reads go the unverified way
  Serial.setRxBufferSize(2048);
  Serial.begin(SERPROG_BAUD);
  Serial.setTimeout(1000);
  if (wifiWanted()) xTaskCreatePinnedToCore(webTask, "web", 8192, nullptr, 1, nullptr, 0);
}

void loop() {
  if (driving && millis() - lastOp > IDLE_MS) pinsOff();
  if (!Serial.available()) return;
  uint8_t cmd = Serial.read();
  switch (cmd) {
    case S_NOP: Serial.write(ACK); break;
    case Q_IFACE: Serial.write(ACK); Serial.write((uint8_t)0x01); Serial.write((uint8_t)0x00); break;
    case Q_CMDMAP: {
      uint8_t map[32] = {0};
      for (uint8_t c : SUPPORTED) map[c >> 3] |= 1 << (c & 7);
      Serial.write(ACK);
      Serial.write(map, 32);
      break;
    }
    case Q_PGMNAME: {
      char name[16] = {0};
      strncpy(name, VARIANT, sizeof(name) - 1);
      Serial.write(ACK);
      Serial.write((const uint8_t *)name, 16);
      break;
    }
    case Q_SERBUF: Serial.write(ACK); Serial.write((uint8_t)0xFF); Serial.write((uint8_t)0x00); break;
    case Q_BUSTYPE: Serial.write(ACK); Serial.write((uint8_t)0x08); break;  // SPI only
    case Q_WRNMAXLEN: Serial.write(ACK); send24(256); break;
    case SYNCNOP: Serial.write(NAK); Serial.write(ACK); break;
    case Q_RDNMAXLEN: Serial.write(ACK); send24(MAX_READ); break;
    case S_BUSTYPE: { uint8_t b = 0; readN(&b, 1); Serial.write((b & 0x08) && !(b & ~0x08) ? ACK : NAK); break; }
    case O_SPIOP: spiOp(); break;
    case S_SPI_FREQ: {
      uint8_t b[4] = {0, 0, 0, 0};
      readN(b, 4);
      uint32_t want = b[0] | (b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
      if (!want) { Serial.write(NAK); break; }
      freq = want < 100000 ? 100000 : (want > 20000000 ? 20000000 : want);
      Serial.write(ACK);
      uint8_t o[4] = {(uint8_t)freq, (uint8_t)(freq >> 8), (uint8_t)(freq >> 16), (uint8_t)(freq >> 24)};
      Serial.write(o, 4);
      break;
    }
    case S_PIN_STATE: {
      uint8_t on = 0;
      readN(&on, 1);
      if (on) { pinsOn(); lastOp = millis(); } else pinsOff();
      Serial.write(ACK);
      break;
    }
    case Q_NETINFO: {  // our own query, outside serprog's range (flashrom never sends it): the live view's address
      IPAddress ip = WiFi.status() == WL_CONNECTED ? WiFi.localIP() : IPAddress(0, 0, 0, 0);
      Serial.write(ACK);
      for (int i = 0; i < 4; i++) Serial.write((uint8_t)ip[i]);
      Serial.write((uint8_t)(wifiWanted() ? WiFi.status() : 255));
      break;
    }
    default: Serial.write(NAK); break;
  }
}
