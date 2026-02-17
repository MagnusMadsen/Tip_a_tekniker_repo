#!/usr/bin/env python3
import socket
from pymodbus.server.tcp import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import logging

logging.basicConfig(filename='slave_eth0.log', level=logging.INFO)

# Fake datastore - register 2 starter på 0
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0, 0, 0, 123, 0]*100)  # Reg 2 = 123 fra master
)
context = ModbusServerContext(slaves=store, single=True)

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"eth0")
sock.bind(('172.16.4.51', 502))
sock.listen(5)

print("=== FIKTIV SLAVE på ETH0:502 ===")
print("Venter på masterens værdi i register 2...")

server = ModbusTcpServer(context, address=('172.16.4.51', 502), sock=sock)
server.serve_forever()