#!/usr/bin/env python3
from pymodbus.server import Server
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

# Default slave ID 1
store = ModbusSequentialDataBlock(0, [100]*20)
slave_ctx = ModbusSlaveContext(hr=store)
ctx = ModbusServerContext(slaves=slave_ctx, single=True)

print("Fake Modbus SLAVE til Windows1 (Poll) på 172.16.4.51:502")
server = Server(ctx, address=("172.16.4.51", 502))
server.serve_forever()