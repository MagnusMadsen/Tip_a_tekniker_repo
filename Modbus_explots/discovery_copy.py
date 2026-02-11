#!/usr/bin/env python3
import sys
import time
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

ip = sys.argv[1]
client = ModbusTcpClient(ip, port=502)

if not client.connect():
    raise ConnectionException(f"Kunne ikke forbinde til {ip}:502")

while True:
    rr = client.read_holding_registers(address=1, count=16, unit=255)
    if rr.isError():
        print(f"Modbus error: {rr}")
    else:
        print(rr.registers)
    time.sleep(1)

