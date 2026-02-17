#!/usr/bin/env python3
from pymodbus.client import ModbusTcpClient
import time
import logging

logging.basicConfig(filename='master_eth1.log', level=logging.INFO)

print("=== MASTER på eth1:502 startet ===")
print("Slave (172.16.4.51) kan nu connecte til 172.16.4.50:502")

# Client bundet til eth1
client = ModbusTcpClient("172.16.4.51", port=502, source_address=("172.16.4.50", 502))

try:
    client.connect()
    while True:
        # Læs holding registers (simuler master polling)
        result = client.read_holding_registers(0, 10, unit=1)
        if not result.isError():
            print(f"Læst: {result.registers}")
            logging.info(f"Læst registers: {result.registers}")
        time.sleep(2)
finally:
    client.close()