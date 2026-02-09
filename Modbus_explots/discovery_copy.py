#!/usr/bin/env python3
import time
from pymodbus.client import ModbusTcpClient

ip = "127.0.0.1"
client = ModbusTcpClient(ip, port=502)

if not client.connect():
    raise SystemExit(f"Kunne ikke forbinde til {ip}:502")

while True:
    rr = client.read_input_registers(0, 16, unit=1)
    if rr.isError():
        print(rr)
    else:
        print(rr.registers)
    time.sleep(1)


