"""Ask espserprog for its live view's address over the serial port (its own query 0xF0, J-214). Needs pyserial.

Opening the port may reset the dev board (its DTR/RTS auto-reset), so the script asks every second for up to 20 s,
until the Wi-Fi has joined.

Usage:  python -I tools/espserprog/netinfo.py COM<n>
"""

import sys
import time

import serial

STATUS = {0: "idle", 1: "network not found", 3: "connected", 4: "connection failed", 5: "connection lost",
          6: "disconnected", 255: "built without Wi-Fi"}


def main() -> int:
    p = serial.Serial(sys.argv[1], 921600, timeout=1)
    time.sleep(1.0)
    deadline = time.monotonic() + 20
    while True:
        p.reset_input_buffer()
        p.write(b"\xf0")
        r = p.read(6)
        if len(r) != 6 or r[0] != 0x06:
            print(f"no answer ({r.hex(' ')}): an older espserprog without the query?")
            return 2
        if r[5] in (3, 255) or time.monotonic() > deadline:
            break
        time.sleep(1)
    ip = ".".join(str(b) for b in r[1:5])
    print(f"Wi-Fi: {STATUS.get(r[5], r[5])}; live view: "
          + (f"http://{ip}/ (or http://espserprog.local/)" if ip != "0.0.0.0" else "-"))
    return 0 if r[5] == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
