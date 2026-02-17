#!/usr/bin/env python3
from pymodbus.server import Server
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

store = ModbusSequentialDataBlock(0, [200]*20)
slave_ctx = ModbusSlaveContext(hr=store)
ctx = ModbusServerContext(slaves=slave_ctx, single=True)

print("Fake Modbus MASTER til Windows2 (Slave) på 172.16.4.50:502")
server = Server(ctx, address=("172.16.4.50", 502))
server.serve_forever()