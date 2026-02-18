#!/usr/bin/env python3
from pymodbus.client import ModbusTcpClient

TARGET_IP = "172.16.4.51"   # <-- ret til slave IP
PORT = 502
UNIT_ID = 1                  # <-- ret hvis anden unit id

# reg 2: de fleste enheder = 1-based "register number" => address=1
ADDRESS = 1

client = ModbusTcpClient(host=TARGET_IP, port=PORT)

if not client.connect():
    print("[-] Could not connect")
    raise SystemExit(1)

resp = client.write_register(address=ADDRESS, value=999, slave=UNIT_ID)

if resp.isError():
    print(f"[-] Write failed: {resp}")
    print("[*] Tip: prøv ADDRESS=2 hvis din enhed bruger 0-based addressing")
else:
    print("[+] OK: wrote 999 to reg 2")

client.close()
