#!/usr/bin/env python3
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import logging

# Logging til fil
logging.basicConfig(filename='slave_eth0.log', level=logging.INFO)

# Fake data (du kan ændre disse værdier manuelt)
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [42, 100, 200, 300]*25)  # Holding registers
)
context = ModbusServerContext(slaves=store, single=True)

print("=== SLAVE på eth0:502 startet ===")
print("Master (172.16.4.50) kan nu connecte til 172.16.4.51:502")
StartTcpServer(context, address=("172.16.4.51", 502), custom_functions=[])