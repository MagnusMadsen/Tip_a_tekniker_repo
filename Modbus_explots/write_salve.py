#!/usr/bin/env python3
import sys
import time
from pymodbus.client.sync import ModbusTcpClient

IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 502
UNIT = 1
ADDR = 2
VALUES = [999, 123]
INTERVAL = 1.0

client = ModbusTcpClient(IP, port=PORT, timeout=2)
if not client.connect():
    print(f"[!] Could not connect to {IP}:{PORT}")
    raise SystemExit(1)

print(f"[+] Connected to {IP}:{PORT} (unit={UNIT})")

i = 0
try:
    while True:
        v = VALUES[i % len(VALUES)]
        wr = client.write_register(ADDR, v, unit=UNIT)
        if wr.isError():
            print(f"[!] Write error: {wr}")
        else:
            rr = client.read_holding_registers(ADDR, 1, unit=UNIT)
            if rr.isError():
                print(f"[!] Readback error: {rr}")
            else:
                print(f"[+] Wrote HR[{ADDR}]={v} (readback={rr.registers[0]})")
        i += 1
        time.sleep(INTERVAL)
finally:
    client.close()
