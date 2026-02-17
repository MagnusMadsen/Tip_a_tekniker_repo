#!/usr/bin/env python3
import logging
from datetime import datetime
from pymodbus.server import StartTcpServer

# Kompatibel datastore-import (pymodbus varierer)
try:
    from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext, ModbusSparseDataBlock
    NEW_API = True
except Exception:
    from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
    NEW_API = False

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 502
UNIT_ID = 1
REG_COUNT = 100

LOG_FILE = "modbus_slave.log"

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Logger: alt til fil, minimalt til terminal
logger = logging.getLogger("modbus_slave")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
logger.addHandler(fh)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(sh)

class LoggedHR(ModbusSparseDataBlock):
    def getValues(self, address, count=1):
        values = super().getValues(address, count)
        logger.debug(f"HR READ  addr={address} count={count} -> {values}")
        return values

    def setValues(self, address, values):
        values = list(values)
        old = super().getValues(address, len(values))
        logger.debug(f"HR WRITE addr={address} values={values} (old={old})")

        # Terminal: kun hvis master sender noget "nyt" (ændring)
        if list(old) != values:
            logger.info(f"[{ts()}] MASTER WRITE: addr={address} values={values}")

        return super().setValues(address, values)

def main():
    hr = LoggedHR({i: 0 for i in range(REG_COUNT)})

    if NEW_API:
        device = ModbusDeviceContext(hr=hr)
        context = ModbusServerContext(devices=device, single=True)
    else:
        slave = ModbusSlaveContext(hr=hr)
        context = ModbusServerContext(slaves={UNIT_ID: slave}, single=False)

    logger.info(f"[{ts()}] Starting Modbus SLAVE on {LISTEN_IP}:{LISTEN_PORT} unit={UNIT_ID}")
    logger.info(f"[{ts()}] Logging details to: {LOG_FILE}")
    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))

if __name__ == "__main__":
    main()
