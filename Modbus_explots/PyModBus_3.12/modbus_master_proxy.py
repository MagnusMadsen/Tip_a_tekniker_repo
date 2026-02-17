#!/usr/bin/env python3
from pymodbus.client.tcp import ModbusTcpClient
import time
import logging

logging.basicConfig(filename='master_eth1.log', level=logging.INFO)

# Bind til eth1
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"eth1")

client = ModbusTcpClient("172.16.4.51", port=502, source_address=("172.16.4.50", 502), socket=sock)

print("=== FIKTIV MASTER på ETH1:502 ===")
print("Skriver 43 til register 2 hvert 2. sekund...")

try:
    client.connect()
    while True:
        # SKRIV 43 til register 2
        result = client.write_register(2, 43, unit=1)
        if not result.isError():
            print("✓ Skrev 43 til reg 2")
            logging.info("Skrev 43 til reg 2")
        
        # LÆS register 2 tilbage (bekræft)
        read_result = client.read_holding_registers(2, 1, unit=1)
        if not read_result.isError():
            print(f"Reg 2 indeholder nu: {read_result.registers[0]}")
        
        time.sleep(2)
finally:
    client.close()