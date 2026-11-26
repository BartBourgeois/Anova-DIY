"""The CC3220 connect step for cc3200tool, run by `ccx.py --cc3220` inside cc3200tool's virtual environment.

cc3200tool takes `chip type & 0x10` for a CC3200 and refuses a CC3220S boot loader below version 4 ("Unsupported
device"). TI's SWPA230A gives the CC3220 path (table 10, section 5.3.3): Switch UART to APPS MCU (opcode 0x33,
delay 26666667 ticks = 1 s), then a break that the network processor must sense while it powers up, answered with
an ACK. This module replaces cc3200tool's switch_to_nwp_bootloader with that step alone: no SRAM patch (TI's steps
4-7), no flash operation.

The break is held for a window instead of cc3200tool's 200 ms pulses one second after the switch: when the network
processor misses it, it boots its own firmware, which wrote two blocks of the LaunchPad's flash (J-160). So:
- the break goes on LEAD seconds after the switch's ACK and stays on for HOLD seconds, whatever arrives meanwhile;
- every byte received from the switch's ACK on is logged with its time, so the ACK's arrival can be timed;
- then the version query must come back from the network processor's boot loader (major version 1, the ROM's is 0);
- a miss is an error that needs a reset, never a retry.

LEAD and HOLD come from the environment (CCX_BREAK_LEAD, CCX_BREAK_HOLD, in seconds; ccx.py sets them from
--break-lead/--break-hold).
"""

import os
import struct
import sys
import time

import cc3200tool.cc as cc

SWITCH_DELAY = 26666667  # ticks; "One second is required, hence, the value 26666667 must be used" (SWPA230A table 10)
LEAD = float(os.environ.get("CCX_BREAK_LEAD", "0.5"))
HOLD = float(os.environ.get("CCX_BREAK_HOLD", "1.5"))
AFTER = 0.3  # s to keep listening after the break is released


def switch(self):
    cc.log.info("ccx --cc3220: Switch UART to APPS MCU (0x33), break held %.2f-%.2f s after its ACK, no RAM patch",
                LEAD, LEAD + HOLD)
    self._send_packet(cc.OPCODE_SWITCH_2_APPS + struct.pack(">I", SWITCH_DELAY))
    t0 = time.monotonic()
    rx = []  # (seconds after the switch's ACK, bytes)

    def listen(until):
        while (now := time.monotonic()) < until:
            self.port.timeout = min(0.02, max(until - now, 0.001))
            data = self.port.read(64)
            if data:
                rx.append((time.monotonic() - t0, data))

    timeout = self.port.timeout  # cc3200tool's own reads rely on it
    try:
        listen(t0 + LEAD)
        self.port.break_condition = True
        try:
            listen(t0 + LEAD + HOLD)
        finally:
            self.port.break_condition = False
        listen(time.monotonic() + AFTER)
    finally:
        self.port.timeout = timeout
    stream = b"".join(d for _, d in rx)
    for t, d in rx:
        cc.log.info("ccx --cc3220: +%.3f s rx %s", t, d.hex(" "))
    acks = stream.count(b"\x00\xcc")
    cc.log.info("ccx --cc3220: %d ACK(s) in %d bytes received", acks, len(stream))
    if not acks:
        raise cc.CC3200Error("no ACK to the break: the network processor may be running its own firmware now (J-160); "
                             "reset before anything else")
    self.vinfo_apps = self._get_version()
    if self.vinfo_apps.bootloader[0] < 1:
        raise cc.CC3200Error(f"the ROM answered, not the network processor: {self.vinfo_apps}; reset")
    cc.log.info("ccx --cc3220: network processor boot loader %s", ".".join(map(str, self.vinfo_apps.bootloader)))
    if STATUS:
        device_status(self)


STATUS = os.environ.get("CCX_STATUS") == "1"  # ccx.py --status (alias --fs-usage)
OPCODE_GET_FS_USAGE = b"\x37"  # TI's SL_BOOTLDR_OPCODE_GET_FS_USAGE (Image Creator's slconsts, J-194)
OPCODE_GET_DEVICE_PARAM = b"\x3a"  # SL_BOOTLDR_OPCODE_GET_DEVICE_PARAM; 0x38 and 0x39 next to it are writes (J-195)
DEVICE_PARAM_DEFAULT_MAC_ADDR = 0  # TI's DeviceParams
USAGE_FIELDS = ("DeviceBlockSize", "DeviceBlocksCapacity", "NumOfAllocatedBlocks", "NumOfReservedBlocks",
                "NumOfReservedBlocksForSystemfiles", "LargestAllocatedGapInBlocks", "NumOfAvailableBlocksForUserFiles")
FS_FIELDS = ("MaxFsFiles", "IsDevlopmentFormatType", "Bundlestate", "CC3200_BundleState",
             "MaxFsFilesReservedForSysFiles", "ActualNumOfUserFiles", "ActualNumOfSysFiles")


def fs_usage(self):
    """GET_FS_USAGE (0x37), the query behind Image Creator's mode and alert count (slbootloader._get_fs_usage_info,
    _is_dev_mode, _get_alerts; J-194): the packet, its ACK, one reply packet, the reply's ACK. The reply is TI's
    ctypes FileSysControlDeviceInfo_t, a BigEndianStructure with natural alignment: seven u16 of block usage (14
    bytes, 2 bytes padding), then eight u8, NumOfAlerts u32, NumOfAlertsThreshold u32, FATWriteCounter u16, padding
    u16 (36 bytes in all; the LaunchPad's reply: block size 4096, 1024 blocks, threshold 15). A read: Uniflash asks it at every connect, also on a production chip, without an
    alert (J-163, J-179)."""
    self._send_packet(OPCODE_GET_FS_USAGE)
    data = self._read_packet()
    cc.log.info("ccx --cc3220: fs usage, %d bytes: %s", len(data), data.hex(" "))
    if len(data) < 36:
        raise cc.CC3200Error(f"fs usage reply is {len(data)} bytes, TI's layout needs 36; raw bytes logged above")
    usage = dict(zip(USAGE_FIELDS, struct.unpack_from(">7H", data, 0)))
    fs = dict(zip(FS_FIELDS, struct.unpack_from(">7B", data, 16)))
    alerts, threshold, fat_writes = struct.unpack_from(">IIH", data, 24)
    cc.log.info("ccx --cc3220: blocks %s", ", ".join(f"{k}={v}" for k, v in usage.items()))
    cc.log.info("ccx --cc3220: file system %s, FATWriteCounter=%d", ", ".join(f"{k}={v}" for k, v in fs.items()),
                fat_writes)
    cc.log.info("ccx --cc3220: mode %s, security alerts %d of %d",
                "development" if fs["IsDevlopmentFormatType"] else "production", alerts, threshold)
    return usage, fs, alerts, threshold


def device_status(self):
    """Image Creator's "Device status" panel from the boot loader's read queries (J-195), after the switch: GET_FS_USAGE
    (mode, capacity, free space, alerts), GET_STORAGE_INFO of the serial flash (0x31: block size, block count, the
    flash's ID bytes; the query every read_flash makes first) and GET_DEVICE_PARAM (0x3A) with parameter 0, the
    default MAC address (slbootloader._get_default_mac_address: the reply's first six bytes). All three are reads;
    Uniflash's own device info makes the same ones without an alert (J-194). Printed as Uniflash shows it."""
    usage, fs, alerts, threshold = fs_usage(self)
    self._send_packet(cc.OPCODE_GET_STORAGE_INFO + struct.pack(">I", cc.STORAGE_ID_SFLASH))
    sinfo = self._read_packet()
    cc.log.info("ccx --cc3220: storage info (serial flash): %s", sinfo.hex(" "))
    self._send_packet(OPCODE_GET_DEVICE_PARAM + struct.pack(">I", DEVICE_PARAM_DEFAULT_MAC_ADDR))
    param = self._read_packet()
    cc.log.info("ccx --cc3220: device parameter 0 (default MAC): %s", param.hex(" "))
    chip = self.vinfo.chip_type if self.vinfo else (0, 0, 0, 0)
    bsize, bcount = struct.unpack(">HH", sinfo[:4])
    kb = usage["DeviceBlockSize"] // 1024
    rows = [
        ("Connected", "On"),
        ("Device Type", "CC3220, Secure" if chip[0] == 0x18 else f"chip type {chip[0]:#04x}"),
        ("MAC Address", ":".join(f"{b:02x}" for b in param[:6])),
        ("HW Version", str(chip[1])),
        ("Current Mode", "Development" if fs["IsDevlopmentFormatType"] else "Production"),
        ("Storage Capacity", f"{bsize * bcount // 1024}KB"),
        ("Formatted Capacity", f"{usage['DeviceBlocksCapacity'] * kb}KB"),
        ("Available for User Files", f"{usage['NumOfAvailableBlocksForUserFiles'] * kb}KB"),
        ("SFLASH codes", ",".join(f"{b:#x}" for b in sinfo[5:8])),
        ("Security Alerts", f"{alerts} / {threshold}"),
    ]
    cc.log.info("ccx --cc3220: Device status\n%s", "\n".join(f"    {k + ':':26}{v}" for k, v in rows))


def file_info(data):
    """GET_FILE_INFO (0x2A) as a CC3220S answers it (J-172): 36 bytes, flags in bytes 0-1, the file's length in bytes
    4-7 (big-endian), its allocation in bytes 8-11; all zeros for a missing file, and also for secure or system files
    the boot loader doesn't report (/sys/mcuimg.bin, /tmp/phy.cal). cc3200tool's own parser wants byte 0 == 1 (the
    CC3200's form) and so calls every file missing."""
    exists = any(data[:12])
    size = struct.unpack(">I", data[4:8])[0] if exists else 0
    cc.log.info("ccx --cc3220: file info flags %s, length %d, allocated %d", data[:4].hex(" "), size,
                struct.unpack(">I", data[8:12])[0])
    return cc.CC3x00FileInfo(exists, size)


CERT = os.environ.get("CCX_CERT", "")  # the certificate's file name on the device, for a signed write (--cert)
_close_file_cc3200 = cc.CC3200Connection._close_file
_get_fat_info_cc3200 = cc.CC3200Connection.get_fat_info


def write_file_api(self, local_file, cc_filename, sign_data, fs_flags, size, file_data, file_len):
    """cc3200tool's _write_file_api the way TI's Image Creator writes (slbootloader._write_file_buffer, J-174): no
    file-info query and no erase first (on a secure file both act without its token and raise a security alert,
    J-173), then open, the data in 4 KiB chunks, and TI's close."""
    alloc = max(size, file_len)
    effective = alloc * 2 if fs_flags and fs_flags & cc.SLFS_FILE_OPEN_FLAG_COMMIT else alloc
    timeout = self.port.timeout
    if effective > 200000:
        timeout = max(timeout, 5 * ((effective / 200000) + 1))
    cc.log.info("ccx --cc3220: writing %s -> %s, %d bytes, allocation %d, flags %#x, certificate %r",
                local_file.name, cc_filename, file_len, alloc, fs_flags or 0, CERT if sign_data else "")
    with self._serial_timeout(timeout):
        self._open_file_for_write(cc_filename, alloc, fs_flags)
    for pos in range(0, file_len, cc.SLFS_BLOCK_SIZE):
        self._send_packet(cc.OPCODE_FILE_CHUNK + struct.pack(">I", pos) + file_data[pos:pos + cc.SLFS_BLOCK_SIZE])
        if not self._get_last_status().is_ok:
            raise cc.CC3200Error(f"writing at pos {pos} failed")
        sys.stderr.write(".")
        sys.stderr.flush()
    sys.stderr.write("\n")
    self._ccx_writing = True
    try:
        return self._close_file(sign_data)
    finally:
        self._ccx_writing = False


def close_file(self, signature=None):
    """TI's close after a write (slbootloader._close_file, J-174): opcode 0x22, the certificate's file name
    zero-padded to 180 bytes, the signature, a flags byte. cc3200tool's own close puts 63 zero bytes where the name
    goes, so on a CC3220 its signature lands at the wrong offset. The close after a read stays cc3200tool's (no
    alert from it, J-172, J-173)."""
    if not getattr(self, "_ccx_writing", False):
        return _close_file_cc3200(self, signature)
    name = CERT.encode("utf-8") if signature else b""
    if signature and (len(signature) != 256 or not name or len(name) >= 180):
        raise cc.CC3200Error("a signed close needs a 256-byte signature and the certificate's file name (--cert)")
    self._send_packet(cc.OPCODE_FINISH_UPLOAD + name.ljust(180, b"\0") + (signature or b"") + b"\0")
    status = self._get_last_status()
    cc.log.info("ccx --cc3220: close, status %#x", status.value)
    if not status.is_ok:
        raise cc.CC3200Error(f"closing file failed: status {status.value:#x}")


class _NoFat:
    def print_sffs_info_short(self):
        cc.log.info("ccx --cc3220: file-table check after the write skipped (a CC3220S table is encrypted)")


def get_fat_info(self, *args, **kwargs):
    """cc3200tool reads the file table after every write_file (from main); on a CC3220S that table is encrypted and
    the check fails after a write that worked. Every other use is unchanged."""
    if self.port is not None and sys._getframe(1).f_code.co_name == "main":
        return _NoFat()
    return _get_fat_info_cc3200(self, *args, **kwargs)


RESET_TOOL = os.environ.get("CCX_RESET_TOOL")  # TI's xds110reset.exe: hold the break across a reset (SOP1, J-308)
RESET_PROBE = os.environ.get("CCX_RESET_PROBE", "E0081010")  # the LaunchPad's XDS110


def held_break(self, tries=5, timeout=1):
    """With J13 on SOP1 the ROM enters its boot loader only if a break is already on the line when it leaves reset
    (with SOP2 it always waits, and cc3200tool's break two seconds later works). So, on the open port: set the
    break, reset the chip through the XDS110, wait for the ROM's ACK while the break stays on, then clear it. A
    second break after that gets no answer (J-308), which is why this replaces the connect's own break instead of
    preceding it in another process. Used when CCX_RESET_TOOL is set; `--reset none` then."""
    import subprocess
    self.port.reset_input_buffer()
    self.port.break_condition = True
    t0 = time.monotonic()
    seen = bytearray()
    try:
        subprocess.run([RESET_TOOL, "-a", "toggle", "-d", "200", "-s", RESET_PROBE], capture_output=True)
        timeout_saved, self.port.timeout = self.port.timeout, 0.05
        try:
            while time.monotonic() - t0 < 3.0 and b"\x00\xcc" not in seen:
                seen += self.port.read(16)
        finally:
            self.port.timeout = timeout_saved
    finally:
        self.port.break_condition = False
    cc.log.info("ccx --cc3220: break held across the XDS110 reset: %s after %.2f s",
                "ACK" if b"\x00\xcc" in seen else "no ACK", time.monotonic() - t0)
    if b"\x00\xcc" not in seen:
        raise cc.CC3200Error("Did not get ACK on the break held across the reset (the application boots now)")


ROM_ONLY = os.environ.get("CCX_ROM_ONLY") == "1"  # ccx.py --rom-only


def rom_only(self):
    """--rom-only (J-200): stop after the ROM boot loader's version reply. No Switch UART to APPS, so the network
    processor is never started and can't boot its own firmware (which writes /tmp/phy.cal after a missed break,
    J-160, J-186); no RAM upload either (cc3200tool's own switch would upload a DLL to SRAM and run it on a boot
    loader of version 4 and up). What is sent in all: the break and one version query (connect's; the second one
    belongs to the switch this replaces). For a chip whose flash has no backup yet: proof that it and its ROM are
    alive, its chip type and hardware version, nothing more. The mode and the MAC are not to be had here: this boot
    loader ACKs GET_FS_USAGE and GET_DEVICE_PARAM but answers neither (LaunchPad, J-202), and TI's own tool always
    switches before asking them."""
    self.vinfo_apps = None
    chip = self.vinfo.chip_type
    cc.log.info("ccx --rom-only: ROM boot loader %s, chip type %#04x, hardware version %d; stopping here: no switch, "
                "the network processor stays off", ".".join(map(str, self.vinfo.bootloader)), chip[0], chip[1])


def run():
    sys.argv[0] = "cc3200tool"
    cc.CC3200Connection.switch_to_nwp_bootloader = rom_only if ROM_ONLY else switch
    cc.CC3x00FileInfo.from_packet = staticmethod(file_info)
    cc.CC3200Connection._write_file_api = write_file_api
    cc.CC3200Connection._close_file = close_file
    cc.CC3200Connection.get_fat_info = get_fat_info
    if RESET_TOOL:
        cc.CC3200Connection._try_breaking = held_break
    cc.main()
