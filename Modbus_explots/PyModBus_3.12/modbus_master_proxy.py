#!/usr/bin/env python3
import socket
from pymodbus.client.tcp import ModbusTcpClient
import time
import logging

logging.basicConfig(filename='master_eth1.log', level=logging.INFO)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"eth1")

client = ModbusTcpClient("172.16.4.51", port=502, source_address=("172.16.4.50", 502), socket=sock)

print("=== MASTER ETH1:502 ===")
client.connect()

while True:
    client.write_register(2, 43, slave=1)
    result = client.read_holding_registers(2, 1, slave=1)
    print(f"Reg 2: {result.registers}")
    time.sleep(2)