#!/usr/bin/env python3
"""
Simple Modbus TCP slave with:
- Minimal terminal output (startup + only NEW/CHANGED writes)
- Detailed file logging of all HR reads/writes

Works across multiple pymodbus versions (API moved around).
"""

import logging
from datetime import datetime
from pymodbus.server import StartTcpServer

# ---- pymodbus datastore compatibility (newer vs older) ----
try:  # newer pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusDeviceContext, ModbusSparseDataBlock
    NEW_API = True
except Exception:  # older pymodbus
    from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
    NEW_API = False

# ---- config ----
LISTEN_IP, LISTEN_PORT = "172.16.4.51", 502
UNIT_ID, REG_COUNT = 1, 100
LOG_FILE = "modbus_slave.log"


def ts() -> str:
    """Short timestamp for terminal messages."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_logger(path: str) -> logging.Logger:
    """
    Logger policy:
    - Terminal: INFO only (startup + changed writes)
    - File: DEBUG (all reads/writes with values)
    """
    log = logging.getLogger("modbus_slave")
    log.setLevel(logging.DEBUG)
    log.handlers.clear()

    file_h = logging.FileHandler(path)
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))

    term_h = logging.StreamHandler()
    term_h.setLevel(logging.INFO)
    term_h.setFormatter(logging.Formatter("%(message)s"))

    log.addHandler(file_h)
    log.addHandler(term_h)
    return log


def make_context(hr_block):
    """
    Build the server context:
    - Newer pymodbus uses ModbusDeviceContext
    - Older pymodbus uses ModbusSlaveContext + unit-id map
    """
    if NEW_API:
        return ModbusServerContext(devices=ModbusDeviceContext(hr=hr_block), single=True)
    return ModbusServerContext(slaves={UNIT_ID: ModbusSlaveContext(hr=hr_block)}, single=False)


class LoggedHR(ModbusSparseDataBlock):
    """
    Holding register (HR) store that logs:
    - ALL reads/writes to file (DEBUG)
    - Only CHANGED writes to terminal (INFO)
    """
    def __init__(self, size: int, log: logging.Logger):
        super().__init__({i: 0 for i in range(size)})
        self.log = log

    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        self.log.debug(f"HR READ  addr={address} count={count} -> {vals}")
        return vals

    def setValues(self, address, values):
        values = list(values)
        old = list(super().getValues(address, len(values)))
        self.log.debug(f"HR WRITE addr={address} values={values} (old={old})")
        if old != values:
            self.log.info(f"[{ts()}] MASTER WRITE: addr={address} values={values}")
        return super().setValues(address, values)


def main():
    log = make_logger(LOG_FILE)
    hr = LoggedHR(REG_COUNT, log)
    context = make_context(hr)

    log.info(f"[{ts()}] Starting Modbus SLAVE on {LISTEN_IP}:{LISTEN_PORT} unit={UNIT_ID}")
    log.info(f"[{ts()}] Detailed log: {LOG_FILE}")
    StartTcpServer(context, address=(LISTEN_IP, LISTEN_PORT))


if __name__ == "__main__":
    main()
