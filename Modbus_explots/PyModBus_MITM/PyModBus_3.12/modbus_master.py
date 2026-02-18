#!/usr/bin/env python3
import logging  
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

store = ModbusSequentialDataBlock(0, [200]*20)
context = ModbusSlaveContext(hr=store)
context = ModbusServerContext(slaves=context, single=True)

print("Fake Modbus MASTER til Windows2 (Slave) på 172.16.4.50:502") 
StartTcpServer(context, address=("172.16.4.50", 502))