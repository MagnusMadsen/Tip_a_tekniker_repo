#!/usr/bin/env python3
import argparse
import logging
import threading
import time

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext
from pymodbus.datastore.context import ModbusDeviceContext
from pymodbus.server.startstop import StartTcpServer


class LoggingDataBlock(ModbusSequentialDataBlock):
    """
    Logs every Modbus read/write against this block.
    """

    def __init__(self, block_name: str, address: int, values):
        super().__init__(address, values)
        self.block_name = block_name
        self.log = logging.getLogger(f"slave.{block_name}")

    def getValues(self, address, count=1):
        vals = super().getValues(address, count)
        self.log.info("READ  %s addr=%d count=%d -> %s", self.block_name, address, count, vals)
        return vals

    def setValues(self, address, values):
        self.log.info("WRITE %s addr=%d values=%s", self.block_name, address, list(values))
        return super().setValues(address, values)


def make_context(unit_id: int, size: int) -> ModbusServerContext:
    # Dækker adresser 0..size-1 for alle datatyper
    di = LoggingDataBlock("DI", 0, [0] * size)  # Discrete Inputs (02)
    co = LoggingDataBlock("CO", 0, [0] * size)  # Coils (01/05/15)
    hr = LoggingDataBlock("HR", 0, [0] * size)  # Holding Regs (03/06/16)
    ir = LoggingDataBlock("IR", 0, [0] * size)  # Input Regs (04)

    # Demo-værdier (så du kan se noget med det samme)
    hr.setValues(0, [123, 456, 789])
    ir.setValues(0, [111, 222, 333])

    device = ModbusDeviceContext(di=di, co=co, hr=hr, ir=ir)
    return ModbusServerContext(devices={unit_id: device}, single=False)


def start_heartbeat(context: ModbusServerContext, unit_id: int, reg: int, period: float) -> None:
    """
    Opdater HR[reg] hvert 'period' sekund, så du kan se aktivitet.
    """
    log = logging.getLogger("slave.heartbeat")

    def _run():
        value = 0
        while True:
            value = (value + 1) & 0xFFFF
            try:
                log.info("HEARTBEAT write HR addr=%d value=%d", reg, value)
                context[unit_id].setValues(3, reg, [value])  # 3 = Holding Registers
            except Exception as e:
                log.exception("Heartbeat failed: %s", e)
            time.sleep(period)

    threading.Thread(target=_run, daemon=True).start()


def main():
    p = argparse.ArgumentParser(description="Modbus TCP slave with verbose terminal logging (pymodbus 3.12.1)")
    p.add_argument("--host", default="0.0.0.0", help="IP to bind (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=502, help="TCP port (default: 502)")
    p.add_argument("--unit", type=int, default=1, help="Unit ID (default: 1)")
    p.add_argument("--size", type=int, default=10000, help="Register/coil space size (default: 10000)")
    p.add_argument("--heartbeat-reg", type=int, default=0, help="Holding register to increment (default: 0)")
    p.add_argument("--heartbeat", type=float, default=1.0, help="Heartbeat period seconds (default: 1.0; 0 disables)")
    p.add_argument("--debug", action="store_true", help="Enable pymodbus DEBUG logs too")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if args.debug:
        logging.getLogger("pymodbus").setLevel(logging.DEBUG)

    context = make_context(args.unit, args.size)

    if args.heartbeat and args.heartbeat > 0:
        start_heartbeat(context, args.unit, args.heartbeat_reg, args.heartbeat)

    logging.getLogger("slave").info(
        "Starting Modbus TCP slave on %s:%d unit=%d size=%d",
        args.host, args.port, args.unit, args.size
    )

    StartTcpServer(context=context, address=(args.host, args.port))


if __name__ == "__main__":
    main()