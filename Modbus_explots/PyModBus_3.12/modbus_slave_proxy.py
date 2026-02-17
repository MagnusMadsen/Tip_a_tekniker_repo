#!/usr/bin/env python3
import socket
from pymodbus.server.tcp import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import logging

logging.basicConfig(filename='slave_eth0.log', level=logging.INFO)

store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0, 0, 123, 0]*100))
context = ModbusServerContext(slaves=store, single=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"eth0")
sock.bind(('172.16.4.51', 502))
sock.listen(5)

print("=== SLAVE ETH0:502 ===")
server = ModbusTcpServer(context, address=None, sock=sock)
server.serve_forever()