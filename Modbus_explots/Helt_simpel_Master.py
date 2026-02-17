#!/usr/bin/env python3
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ModbusException

TARGET_IP = "172.16.4.51"   # <-- ret til slave IP
TARGET_PORT = 502
UNIT_ID = 1                 # <-- ret hvis anden slave-id

client = ModbusTcpClient(TARGET_IP, port=TARGET_PORT)

if not client.connect():
    print("[-] Connection failed")
    exit(1)

try:
    # Skriv 999 til holding register 2
    # pymodbus bruger 0-based addressing -> reg 2 = address 1
    rr = client.write_register(address=1, value=999, unit=UNIT_ID)

    if rr.isError():
        print(f"[-] Write failed: {rr}")
    else:
        print("[+] Successfully wrote 999 to register 2")

except ModbusException as e:
    print(f"[-] Modbus error: {e}")

client.close()
