// j8probe: listen-only probe for the cooker's boards (plan T12/T13; journal J-085, J-086, J-088).
//
// Every channel pin is an input with both pulls off, and nothing in this file drives one: listen_pin() is the only
// place a channel's direction is set, the pulse counter and the UART sniffer only read, and the sniffer routes RX
// only. Reports go out as JSON lines on USB serial and on TCP port 2323; commands come back the same way, and none
// of them can drive a pin.
#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>

#include "driver/gpio.h"
#include "driver/pulse_cnt.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "hal/gpio_ll.h"
#include "pinmap.h"
#include "soc/gpio_struct.h"
#if __has_include("secrets.h")
#include "secrets.h"
#endif
#ifndef AP_PASS
#define AP_PASS "j8probe-ap"
#endif
#ifndef WITH_RADIO_SCAN
#define WITH_RADIO_SCAN 0
#endif
#if WITH_RADIO_SCAN
#include <BLEAdvertisedDevice.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#endif

static const char *FW_VERSION = "0.2.0";
static constexpr int NCH = sizeof(CHANS) / sizeof(CHANS[0]);
static constexpr uint32_t STORM_EDGES = 5000;  // edges in one window before a pin moves to a pulse counter
static constexpr uint16_t TCP_PORT = 2323;
static constexpr int NSNIFF = 2;
static const uart_port_t SNIFF_PORT[NSNIFF] = {UART_NUM_1, UART_NUM_2};  // UART0 is the USB serial
static constexpr int SNIFF_BUF = 8192;  // per sniffer: rides out a burst while the USB link catches up
static constexpr int64_t FAST_WINDOWS_US = 3000000;  // 100 ms windows for the first 3 s after t0, then 1 s

static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static int64_t t0_us = 0;  // time zero: boot, then every power-on seen on a power channel, or the t0 command

// ---------------------------------------------------------------------------------------------------------------
// Output

static WiFiServer server(TCP_PORT);
static WiFiClient client;
static String host;

static void out(const String &line) {
  Serial.println(line);
  if (client && client.connected()) client.println(line);
}

static String jesc_n(const uint8_t *s, size_t n) {  // JSON string body, ASCII only; other bytes as \u00xx
  String o;
  o.reserve(n + 8);
  for (size_t k = 0; k < n; k++) {
    const uint8_t c = s[k];
    if (c == '"' || c == '\\') {
      o += '\\';
      o += (char)c;
    } else if (c < 0x20 || c >= 0x7f) {
      char b[8];
      snprintf(b, sizeof b, "\\u%04x", c);
      o += b;
    } else {
      o += (char)c;
    }
  }
  return o;
}

static String jesc(const char *s) { return jesc_n((const uint8_t *)s, strlen(s)); }

static String rel(int64_t us) {  // seconds since t0
  char b[24];
  snprintf(b, sizeof b, "%.6f", (us - t0_us) / 1e6);
  return b;
}

static void ok(const char *what) { out(String("{\"ev\":\"ok\",\"cmd\":\"") + jesc(what) + "\"}"); }
static void err(const String &msg) { out("{\"ev\":\"err\",\"msg\":\"" + jesc(msg.c_str()) + "\"}"); }

// ---------------------------------------------------------------------------------------------------------------
// Digital channels: an edge interrupt, or a pulse counter once they toggle too fast for it

struct DigState {  // written by on_edge() under mux
  uint32_t edges;
  uint32_t min_hi_us, min_lo_us;
  int64_t last_us;   // 0 = no edge yet
  int64_t first_us;  // first edge since t0, -1 = none yet
  bool storm;        // the interrupt muted itself; loop() hands the pin to a pulse counter
};
static DRAM_ATTR DigState dig[NCH];
static DRAM_ATTR uint8_t gpio_of[NCH];

enum Mode : uint8_t { M_EDGE, M_PCNT, M_MUTED, M_UART, M_ANALOG };
static Mode mode[NCH];
static pcnt_unit_handle_t pcnt_unit[NCH];
static pcnt_channel_handle_t pcnt_chan[NCH];
static bool first_reported[NCH];

static void IRAM_ATTR on_edge(void *arg) {
  const int i = (int)(intptr_t)arg;
  const int64_t now = esp_timer_get_time();
  const int level = gpio_ll_get_level(&GPIO, gpio_of[i]);
  portENTER_CRITICAL_ISR(&mux);
  DigState &d = dig[i];
  if (d.last_us) {
    const uint32_t dt = (uint32_t)(now - d.last_us);  // width of the state that just ended
    if (level) {
      if (dt < d.min_lo_us) d.min_lo_us = dt;
    } else if (dt < d.min_hi_us) {
      d.min_hi_us = dt;
    }
  }
  d.last_us = now;
  if (d.first_us < 0) d.first_us = now;
  if (++d.edges >= STORM_EDGES && !d.storm) {
    d.storm = true;
    gpio_ll_intr_disable(&GPIO, gpio_of[i]);
  }
  portEXIT_CRITICAL_ISR(&mux);
}

// The one place a channel pin's direction is set: input, both pulls off.
static void listen_pin(uint8_t gpio) {
  pinMode(gpio, INPUT);
  gpio_pullup_dis((gpio_num_t)gpio);
  gpio_pulldown_dis((gpio_num_t)gpio);
}

static void start_edge(int i) {
  listen_pin(CHANS[i].gpio);
  portENTER_CRITICAL(&mux);
  dig[i].edges = 0;
  dig[i].min_hi_us = dig[i].min_lo_us = UINT32_MAX;
  dig[i].last_us = 0;
  dig[i].storm = false;
  portEXIT_CRITICAL(&mux);
  attachInterruptArg(CHANS[i].gpio, on_edge, (void *)(intptr_t)i, CHANGE);
  mode[i] = M_EDGE;
}

static bool start_pcnt(int i) {
  detachInterrupt(CHANS[i].gpio);
  pcnt_unit_config_t uc = {};
  uc.low_limit = -1;
  uc.high_limit = 30000;
  uc.flags.accum_count = 1;
  pcnt_unit_handle_t u = nullptr;
  if (pcnt_new_unit(&uc, &u) != ESP_OK) return false;
  pcnt_chan_config_t cc = {};
  cc.edge_gpio_num = CHANS[i].gpio;
  cc.level_gpio_num = -1;
  pcnt_channel_handle_t ch = nullptr;
  if (pcnt_new_channel(u, &cc, &ch) != ESP_OK) {
    pcnt_del_unit(u);
    return false;
  }
  gpio_pullup_dis((gpio_num_t)CHANS[i].gpio);  // the driver turns a pull-up on for its input
  gpio_pulldown_dis((gpio_num_t)CHANS[i].gpio);
  pcnt_channel_set_edge_action(ch, PCNT_CHANNEL_EDGE_ACTION_INCREASE, PCNT_CHANNEL_EDGE_ACTION_INCREASE);
  pcnt_unit_add_watch_point(u, uc.high_limit);
  pcnt_unit_enable(u);
  pcnt_unit_clear_count(u);
  pcnt_unit_start(u);
  pcnt_unit[i] = u;
  pcnt_chan[i] = ch;
  mode[i] = M_PCNT;
  return true;
}

static void stop_pcnt(int i) {
  pcnt_unit_stop(pcnt_unit[i]);
  pcnt_unit_disable(pcnt_unit[i]);
  pcnt_del_channel(pcnt_chan[i]);
  pcnt_del_unit(pcnt_unit[i]);
  pcnt_unit[i] = nullptr;
  pcnt_chan[i] = nullptr;
}

static void release_digital(int i) {  // whatever listens on the pin now stops
  if (mode[i] == M_PCNT) stop_pcnt(i);
  else if (mode[i] == M_EDGE || mode[i] == M_MUTED) detachInterrupt(CHANS[i].gpio);
}

static void storm_poll() {
  for (int i = 0; i < NCH; i++) {
    if (mode[i] != M_EDGE || !dig[i].storm) continue;
    if (start_pcnt(i)) {
      out("{\"ev\":\"pcnt\",\"ch\":\"" + jesc(CHANS[i].name) + "\",\"why\":\"over 5000 edges in one window\"}");
    } else {
      detachInterrupt(CHANS[i].gpio);
      mode[i] = M_MUTED;
      out("{\"ev\":\"muted\",\"ch\":\"" + jesc(CHANS[i].name) + "\",\"why\":\"edge storm, no pulse counter free\"}");
    }
  }
}

static const uint32_t BAUDS[] = {1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600};

static uint32_t guess_baud(uint32_t min_us) {  // shortest pulse = one bit time, if the line is a UART
  if (!min_us || min_us == UINT32_MAX) return 0;
  const float b = 1e6f / min_us;
  for (uint32_t s : BAUDS)
    if (b > s * 0.85f && b < s * 1.15f) return s;
  return 0;
}

// ---------------------------------------------------------------------------------------------------------------
// UART sniffers: RX only, two digital channels at a time

struct Sniffer {
  int ch;  // channel index, -1 = free
  uint32_t baud;
  QueueHandle_t events;
  uint8_t buf[96];
  size_t len;
  uint32_t last_ms;
  int64_t t_us;
  uint32_t frame_err, overflow;  // since the last event: many framing errors usually mean the wrong baud
};
static Sniffer sniff[NSNIFF] = {{-1}, {-1}};

static int sniffer_of(int i) {  // the sniffer on channel i, or -1
  for (int k = 0; k < NSNIFF; k++)
    if (sniff[k].ch == i) return k;
  return -1;
}

static int free_sniffer() {
  for (int k = 0; k < NSNIFF; k++)
    if (sniff[k].ch < 0) return k;
  return -1;
}

static void uart_flush_event(Sniffer &s) {
  if (!s.len && !s.frame_err && !s.overflow) return;
  // txt is lossless: printable ASCII as is, every other byte as \u00xx
  String line = "{\"ev\":\"uart\",\"ch\":\"" + jesc(CHANS[s.ch].name) + "\",\"baud\":" + s.baud + ",\"t\":" +
                rel(s.t_us) + ",\"n\":" + (unsigned)s.len + ",\"txt\":\"" + jesc_n(s.buf, s.len) + "\"";
  if (s.frame_err) {
    line += ",\"fe\":";
    line += s.frame_err;
  }
  if (s.overflow) {
    line += ",\"ovf\":";
    line += s.overflow;
  }
  out(line + "}");
  s.len = 0;
  s.frame_err = s.overflow = 0;
}

static void stop_uart(int k) {
  Sniffer &s = sniff[k];
  if (s.ch < 0) return;
  uart_flush_event(s);
  uart_driver_delete(SNIFF_PORT[k]);
  const int i = s.ch;
  s.ch = -1;
  s.events = nullptr;
  start_edge(i);
}

static bool start_uart(int i, uint32_t baud) {  // false if no sniffer is free or the driver fails
  int k = sniffer_of(i);
  if (k >= 0) stop_uart(k);
  else k = free_sniffer();
  if (k < 0) return false;
  release_digital(i);
  uart_config_t c = {};
  c.baud_rate = (int)baud;
  c.data_bits = UART_DATA_8_BITS;
  c.parity = UART_PARITY_DISABLE;
  c.stop_bits = UART_STOP_BITS_1;
  c.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  c.source_clk = UART_SCLK_DEFAULT;
  QueueHandle_t q = nullptr;
  if (uart_driver_install(SNIFF_PORT[k], SNIFF_BUF, 0, 16, &q, 0) != ESP_OK) {
    start_edge(i);
    return false;
  }
  uart_param_config(SNIFF_PORT[k], &c);
  // RX only. TX, RTS and CTS stay unrouted, so the UART has no pin it could drive.
  uart_set_pin(SNIFF_PORT[k], UART_PIN_NO_CHANGE, CHANS[i].gpio, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
  gpio_pullup_dis((gpio_num_t)CHANS[i].gpio);
  gpio_pulldown_dis((gpio_num_t)CHANS[i].gpio);
  Sniffer &s = sniff[k];
  s.ch = i;
  s.baud = baud;
  s.events = q;
  s.len = 0;
  s.frame_err = s.overflow = 0;
  mode[i] = M_UART;
  out("{\"ev\":\"uart_on\",\"ch\":\"" + jesc(CHANS[i].name) + "\",\"baud\":" + baud + "}");
  return true;
}

static void uart_poll() {
  for (int k = 0; k < NSNIFF; k++) {
    Sniffer &s = sniff[k];
    if (s.ch < 0) continue;
    uart_event_t e;
    while (xQueueReceive(s.events, &e, 0) == pdTRUE) {
      if (e.type == UART_FRAME_ERR || e.type == UART_PARITY_ERR || e.type == UART_BREAK) s.frame_err++;
      else if (e.type == UART_FIFO_OVF || e.type == UART_BUFFER_FULL) s.overflow++;
    }
    const int n = uart_read_bytes(SNIFF_PORT[k], s.buf + s.len, sizeof s.buf - s.len, 0);
    if (n > 0) {
      if (!s.len) s.t_us = esp_timer_get_time();
      s.len += n;
      s.last_ms = millis();
    }
    const bool pending = s.len || s.frame_err || s.overflow;
    if (s.len == sizeof s.buf || (pending && millis() - s.last_ms > 50)) uart_flush_event(s);
  }
}

// ---------------------------------------------------------------------------------------------------------------
// Analog channels: sampled at 1 kHz by their own task; power channels set t0

struct AnaState {
  float vmin, vmax;
  double vsum;
  uint32_t n, cross;
  bool hi;
};
static AnaState ana[NCH];
struct PowerEv {
  int8_t ch;
  bool on;
  int64_t t_us;
};
static QueueHandle_t power_q;
static bool sampler_power[NCH];  // the sampler's view
static bool power_state[NCH];    // loop()'s view

static void sampler(void *) {
  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(1));
    const int64_t now = esp_timer_get_time();
    for (int i = 0; i < NCH; i++) {
      if (CHANS[i].kind != CH_ANALOG) continue;
      const float pin_v = analogReadMilliVolts(CHANS[i].gpio) / 1000.0f;
      const float v = pin_v * CHANS[i].scale;
      portENTER_CRITICAL(&mux);
      AnaState &a = ana[i];
      if (!a.n || v < a.vmin) a.vmin = v;
      if (!a.n || v > a.vmax) a.vmax = v;
      a.vsum += v;
      a.n++;
      if (!a.hi && pin_v > 1.8f) {  // logic-level toggles, with hysteresis
        a.hi = true;
        a.cross++;
      } else if (a.hi && pin_v < 1.2f) {
        a.hi = false;
        a.cross++;
      }
      portEXIT_CRITICAL(&mux);
      if (CHANS[i].on_v > 0) {
        const bool on = sampler_power[i] ? v > 1.0f : v > CHANS[i].on_v;
        if (on != sampler_power[i]) {
          sampler_power[i] = on;
          PowerEv e{(int8_t)i, on, now};
          xQueueSend(power_q, &e, 0);
        }
      }
    }
  }
}

static void set_t0(int64_t t, const char *why) {
  t0_us = t;
  portENTER_CRITICAL(&mux);
  for (int i = 0; i < NCH; i++)
    if (dig[i].first_us < t) dig[i].first_us = -1;
  portEXIT_CRITICAL(&mux);
  for (int i = 0; i < NCH; i++) first_reported[i] = false;
  char up[24];
  snprintf(up, sizeof up, "%.6f", t / 1e6);
  out(String("{\"ev\":\"t0\",\"up\":") + up + ",\"why\":\"" + jesc(why) + "\"}");
}

static void power_poll() {
  PowerEv e;
  while (xQueueReceive(power_q, &e, 0) == pdTRUE) {
    bool other_on = false;
    for (int i = 0; i < NCH; i++)
      if (i != e.ch && power_state[i]) other_on = true;
    power_state[e.ch] = e.on;
    if (e.on && !other_on) set_t0(e.t_us, CHANS[e.ch].name);
    out("{\"ev\":\"power\",\"ch\":\"" + jesc(CHANS[e.ch].name) + "\",\"on\":" + (e.on ? "true" : "false") +
        ",\"t\":" + rel(e.t_us) + "}");
  }
}

// ---------------------------------------------------------------------------------------------------------------
// Windows: one JSON line per window with every channel

static int32_t fixed_win_ms = 0;  // 0 = automatic
static uint32_t win_start_ms = 0;

static uint32_t window_ms() {
  if (fixed_win_ms) return fixed_win_ms;
  return esp_timer_get_time() - t0_us < FAST_WINDOWS_US ? 100 : 1000;
}

static void report_window(uint32_t win_ms) {
  const int64_t now = esp_timer_get_time();
  String s;
  s.reserve(1200);
  s += "{\"t\":" + rel(now) + ",\"win\":" + win_ms + ",\"ch\":{";
  String firsts;
  for (int i = 0; i < NCH; i++) {
    char b[160];
    if (i) s += ',';
    if (mode[i] == M_ANALOG) {
      portENTER_CRITICAL(&mux);
      AnaState a = ana[i];
      ana[i].n = 0;
      ana[i].vsum = 0;
      ana[i].cross = 0;
      portEXIT_CRITICAL(&mux);
      if (a.n)
        snprintf(b, sizeof b, "\"%s\":{\"v\":[%.3f,%.3f,%.3f],\"x\":%lu}", CHANS[i].name, a.vmin, a.vsum / a.n, a.vmax,
                 (unsigned long)a.cross);
      else
        snprintf(b, sizeof b, "\"%s\":{\"v\":null}", CHANS[i].name);
      s += b;
      continue;
    }
    portENTER_CRITICAL(&mux);
    DigState d = dig[i];
    dig[i].edges = 0;
    dig[i].min_hi_us = dig[i].min_lo_us = UINT32_MAX;
    portEXIT_CRITICAL(&mux);
    uint32_t edges = d.edges;
    if (mode[i] == M_PCNT) {
      int count = 0;
      pcnt_unit_get_count(pcnt_unit[i], &count);
      pcnt_unit_clear_count(pcnt_unit[i]);
      edges = (uint32_t)count;
    }
    int n = snprintf(b, sizeof b, "\"%s\":{\"l\":%d,\"e\":%lu", CHANS[i].name, digitalRead(CHANS[i].gpio),
                     (unsigned long)edges);
    if (d.min_hi_us != UINT32_MAX) n += snprintf(b + n, sizeof b - n, ",\"hi\":%lu", (unsigned long)d.min_hi_us);
    if (d.min_lo_us != UINT32_MAX) n += snprintf(b + n, sizeof b - n, ",\"lo\":%lu", (unsigned long)d.min_lo_us);
    if (d.edges >= 10) {
      const uint32_t bd = guess_baud(min(d.min_hi_us, d.min_lo_us));
      if (bd) n += snprintf(b + n, sizeof b - n, ",\"bd\":%lu", (unsigned long)bd);
    }
    if (mode[i] == M_PCNT) n += snprintf(b + n, sizeof b - n, ",\"pc\":1");
    if (mode[i] == M_MUTED) n += snprintf(b + n, sizeof b - n, ",\"muted\":1");
    if (mode[i] == M_UART) n += snprintf(b + n, sizeof b - n, ",\"uart\":%lu", (unsigned long)sniff[sniffer_of(i)].baud);
    snprintf(b + n, sizeof b - n, "}");
    s += b;
    if (d.first_us >= t0_us && !first_reported[i]) {
      first_reported[i] = true;
      firsts += "{\"ev\":\"first\",\"ch\":\"" + jesc(CHANS[i].name) + "\",\"t\":" + rel(d.first_us) + "}\n";
    }
  }
  s += "}}";
  out(s);
  if (firsts.length()) {
    firsts.trim();
    out(firsts);
  }
}

// ---------------------------------------------------------------------------------------------------------------
// Radio scan (aux): passive BLE and Wi-Fi, new devices reported as they appear

#if WITH_RADIO_SCAN
struct BleEv {
  char addr[18];
  int8_t rssi;
  char name[32];
  uint8_t mfg[24];
  uint8_t mfg_len;
};
static QueueHandle_t ble_q;
struct Seen {
  char key[20];
  uint32_t n;
  int8_t rssi;
};
static Seen ble_seen[64], wifi_seen[64];
static int ble_n = 0, wifi_n = 0;
static uint32_t wifi_scan_ms = 0;

class BleCallbacks : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice d) override {
    BleEv e = {};
    strlcpy(e.addr, d.getAddress().toString().c_str(), sizeof e.addr);
    e.rssi = (int8_t)d.getRSSI();
    if (d.haveName()) strlcpy(e.name, d.getName().c_str(), sizeof e.name);
    if (d.haveManufacturerData()) {
      const String m = d.getManufacturerData();
      e.mfg_len = (uint8_t)min((size_t)m.length(), sizeof e.mfg);
      memcpy(e.mfg, m.c_str(), e.mfg_len);
    }
    xQueueSend(ble_q, &e, 0);
  }
};

static bool remember(Seen *table, int &count, const char *key, int8_t rssi) {  // true if new
  for (int k = 0; k < count; k++)
    if (!strcmp(table[k].key, key)) {
      table[k].n++;
      table[k].rssi = rssi;
      return false;
    }
  if (count < 64) {
    strlcpy(table[count].key, key, sizeof table[count].key);
    table[count].n = 1;
    table[count].rssi = rssi;
    count++;
  }
  return true;
}

static void radio_begin() {
  ble_q = xQueueCreate(32, sizeof(BleEv));
  BLEDevice::init("");
  BLEScan *scan = BLEDevice::getScan();
  scan->setAdvertisedDeviceCallbacks(new BleCallbacks(), true);
  scan->setActiveScan(false);  // passive: listen to advertisements, send no scan requests
  scan->setInterval(100);
  scan->setWindow(90);
  scan->start(0, nullptr, false);  // 0 = scan until stopped
}

static void radio_poll() {
  BleEv e;
  while (xQueueReceive(ble_q, &e, 0) == pdTRUE) {
    if (!remember(ble_seen, ble_n, e.addr, e.rssi)) continue;
    String mfg;
    for (int k = 0; k < e.mfg_len; k++) {
      char b[4];
      snprintf(b, sizeof b, "%02x", e.mfg[k]);
      mfg += b;
    }
    out("{\"ev\":\"ble\",\"addr\":\"" + jesc(e.addr) + "\",\"rssi\":" + (int)e.rssi + ",\"name\":\"" + jesc(e.name) +
        "\",\"mfg\":\"" + mfg + "\",\"t\":" + rel(esp_timer_get_time()) + "}");
  }
  const int n = WiFi.scanComplete();
  if (n >= 0) {
    for (int k = 0; k < n; k++) {
      const String bssid = WiFi.BSSIDstr(k);
      if (!remember(wifi_seen, wifi_n, bssid.c_str(), (int8_t)WiFi.RSSI(k))) continue;
      out("{\"ev\":\"wifi\",\"ssid\":\"" + jesc(WiFi.SSID(k).c_str()) + "\",\"bssid\":\"" + bssid +
          "\",\"rssi\":" + WiFi.RSSI(k) + ",\"chan\":" + WiFi.channel(k) + ",\"t\":" + rel(esp_timer_get_time()) +
          "}");
    }
    WiFi.scanDelete();
  } else if (n == WIFI_SCAN_FAILED && millis() - wifi_scan_ms > 10000) {
    wifi_scan_ms = millis();
    WiFi.scanNetworks(true, true);
  }
}

static void radio_list() {
  for (int k = 0; k < ble_n; k++)
    out(String("{\"ev\":\"ble_seen\",\"addr\":\"") + ble_seen[k].key + "\",\"n\":" + ble_seen[k].n +
        ",\"rssi\":" + (int)ble_seen[k].rssi + "}");
  for (int k = 0; k < wifi_n; k++)
    out(String("{\"ev\":\"wifi_seen\",\"bssid\":\"") + wifi_seen[k].key + "\",\"n\":" + wifi_seen[k].n +
        ",\"rssi\":" + (int)wifi_seen[k].rssi + "}");
  ok("radio");
}
#endif

// ---------------------------------------------------------------------------------------------------------------
// Network, hello, commands

static bool mdns_up = false;

static void net_begin() {
  const uint64_t mac = ESP.getEfuseMac();  // the base MAC, little-endian: byte 5 is the last one
  char h[24];
  snprintf(h, sizeof h, "j8probe-%02x%02x%02x", (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
  host = h;
#if defined(WIFI_SSID)
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(h);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
#elif WITH_RADIO_SCAN
  WiFi.mode(WIFI_STA);  // scanning only; reports go over USB
#else
  WiFi.mode(WIFI_AP);
  WiFi.softAP(h, AP_PASS);
#endif
  server.begin();
  server.setNoDelay(true);
}

static void hello() {
  String s = "{\"ev\":\"hello\",\"fw\":\"" + String(FW_VERSION) + "\",\"setup\":\"" SETUP_NAME "\",\"host\":\"" + host +
             "\",\"sta_ip\":\"" + WiFi.localIP().toString() + "\",\"ap_ip\":\"" + WiFi.softAPIP().toString() +
             "\",\"map\":[";
  for (int i = 0; i < NCH; i++) {
    char b[96];
    snprintf(b, sizeof b, "%s{\"ch\":\"%s\",\"gpio\":%u,\"kind\":\"%s\",\"scale\":%.1f}", i ? "," : "", CHANS[i].name,
             (unsigned)CHANS[i].gpio, CHANS[i].kind == CH_ANALOG ? "analog" : "digital", CHANS[i].scale);
    s += b;
  }
  out(s + "]}");
}

static int find_chan(const String &name) {
  for (int i = 0; i < NCH; i++)
    if (name.equalsIgnoreCase(CHANS[i].name)) return i;
  return -1;
}

static void command(String line) {
  line.trim();
  if (!line.length()) return;
  const int sp = line.indexOf(' ');
  const String cmd = sp < 0 ? line : line.substring(0, sp);
  String rest = sp < 0 ? String() : line.substring(sp + 1);
  rest.trim();
  if (cmd == "help") {
    out("{\"ev\":\"help\",\"cmds\":[\"map\",\"t0\",\"window <ms>|0\",\"uart <channel> <baud>\",\"uart off [<channel>]\","
        "\"rearm\",\"radio\"]}");
  } else if (cmd == "map") {
    hello();
  } else if (cmd == "t0") {
    set_t0(esp_timer_get_time(), "command");
  } else if (cmd == "window") {
    const long ms = rest.toInt();
    if (rest == "0" || (ms >= 10 && ms <= 10000)) {
      fixed_win_ms = rest == "0" ? 0 : ms;
      ok("window");
    } else {
      err("window takes 10..10000 ms, or 0 for automatic");
    }
  } else if (cmd == "uart") {
    if (rest == "off" || rest.startsWith("off ")) {
      String name = rest.substring(3);
      name.trim();
      if (!name.length()) {
        for (int k = 0; k < NSNIFF; k++) stop_uart(k);
        ok("uart off");
        return;
      }
      const int i = find_chan(name);
      const int k = i < 0 ? -1 : sniffer_of(i);
      if (k < 0) err("no sniffer on " + name);
      else {
        stop_uart(k);
        ok("uart off");
      }
      return;
    }
    const int ls = rest.lastIndexOf(' ');
    const int i = ls < 0 ? -1 : find_chan(rest.substring(0, ls));
    const long baud = ls < 0 ? 0 : rest.substring(ls + 1).toInt();
    if (i < 0 || CHANS[i].kind != CH_DIGITAL) err("uart <digital channel> <baud>");
    else if (baud < 300 || baud > 2000000) err("baud out of range");
    else if (sniffer_of(i) < 0 && free_sniffer() < 0) err("both sniffers busy: uart off <channel> first");
    else if (!start_uart(i, baud)) err("uart driver failed");
    else ok("uart");
  } else if (cmd == "rearm") {
    for (int i = 0; i < NCH; i++)
      if (mode[i] == M_PCNT || mode[i] == M_MUTED) {
        release_digital(i);
        start_edge(i);
      }
    ok("rearm");
#if WITH_RADIO_SCAN
  } else if (cmd == "radio") {
    radio_list();
#endif
  } else {
    err("unknown command: " + cmd + " (try help)");
  }
}

static String serial_line, tcp_line;

static void read_lines(Stream &in, String &buf) {
  while (in.available()) {
    const char c = (char)in.read();
    if (c == '\n' || c == '\r') {
      if (buf.length()) command(buf);
      buf = "";
    } else if (buf.length() < 120) {
      buf += c;
    }
  }
}

static void net_poll() {
  if (server.hasClient()) {
    WiFiClient c = server.accept();
    if (client) client.stop();  // the newest client wins
    client = c;
    client.setNoDelay(true);
    hello();
  }
  if (!mdns_up && (WiFi.status() == WL_CONNECTED || WiFi.getMode() == WIFI_AP)) {
    mdns_up = MDNS.begin(host.c_str());
    if (mdns_up) MDNS.addService("j8probe", "tcp", TCP_PORT);
    hello();
  }
  read_lines(Serial, serial_line);
  if (client && client.connected()) read_lines(client, tcp_line);
}

// ---------------------------------------------------------------------------------------------------------------

void setup() {
  // Channels first: every pin an input with pulls off, as early as possible after reset.
  for (int i = 0; i < NCH; i++) {
    gpio_of[i] = CHANS[i].gpio;
    dig[i].first_us = -1;
    if (CHANS[i].kind == CH_ANALOG) {
      listen_pin(CHANS[i].gpio);
      analogReadMilliVolts(CHANS[i].gpio);  // attaches the ADC
      gpio_pullup_dis((gpio_num_t)CHANS[i].gpio);
      gpio_pulldown_dis((gpio_num_t)CHANS[i].gpio);
      mode[i] = M_ANALOG;
    } else {
      start_edge(i);
    }
  }
  Serial.setTxBufferSize(4096);  // a burst of sniffed bytes shouldn't stall loop()
  Serial.begin(921600);
  power_q = xQueueCreate(16, sizeof(PowerEv));
  net_begin();
#if WITH_RADIO_SCAN
  radio_begin();
#endif
  xTaskCreatePinnedToCore(sampler, "sampler", 4096, nullptr, 2, nullptr, 1);
  set_t0(0, "boot");
  hello();
  for (const char *const *b = BOOT_UART; *b; b++) {
    const int i = find_chan(*b);
    if (i < 0 || !start_uart(i, BOOT_UART_BAUD)) err(String("boot sniffer failed: ") + *b);
  }
}

void loop() {
  net_poll();
  power_poll();
  storm_poll();
  uart_poll();
#if WITH_RADIO_SCAN
  radio_poll();
#endif
  const uint32_t now_ms = millis();
  if (now_ms - win_start_ms >= window_ms()) {
    report_window(now_ms - win_start_ms);
    win_start_ms = now_ms;
  }
  delay(1);
}
