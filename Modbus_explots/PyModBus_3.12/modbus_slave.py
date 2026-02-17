#!/usr/bin/env python3
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

store = ModbusSequentialDataBlock(0, [100]*20)
context = ModbusSlaveContext(di=store, co=store, hr=store, ir=store)
context = ModbusServerContext(contexts=context)

print("Fake Modbus SLAVE til Windows1 (Poll) på 172.16.4.51:502")
StartTcpServer(context, address=("172.16.4.51", 502))