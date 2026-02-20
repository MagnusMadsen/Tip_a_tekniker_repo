#!/usr/bin/env python3
import argparse
import logging
import sys
import time

from pymodbus.client import ModbusTcpClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def die(msg: str, code: int = 1):
    logging.error(msg)
    sys.exit(code)


def main():
    p = argparse.ArgumentParser(description="Simple Modbus TCP master (client) for testing a slave")
    p.add_argument("--host", required=True, help="Slave IP (e.g. 172.16.4.51)")
    p.add_argument("--port", type=int, default=502, help="Slave port (default: 502)")
    p.add_argument("--unit", type=int, default=1, help="Unit ID (default: 1)")
    p.add_argument("--addr", type=int, default=0, help="Start register address (default: 0)")
    p.add_argument("--count", type=int, default=10, help="Number of registers to read (default: 10)")
    p.add_argument("--write", type=int, default=None, help="If set, write this value to holding register --addr")
    p.add_argument("--interval", type=float, default=1.0, help="Seconds between polls (default: 1.0)")
    args = p.parse_args()

    client = ModbusTcpClient(host=args.host, port=args.port)

    logging.info("Connecting to %s:%d (unit=%d)", args.host, args.port, args.unit)
    if not client.connect():
        die("Could not connect (TCP). Check IP/port/link and namespace routing.")

    try:
        while True:
            if args.write is not None:
                wr = client.write_register(address=args.addr, value=args.write, unit=args.unit)
                if wr.isError():
                    logging.error("WRITE error: %r", wr)
                else:
                    logging.info("WRITE ok: HR[%d]=%d", args.addr, args.write)

            rr = client.read_holding_registers(address=args.addr, count=args.count, unit=args.unit)
            if rr.isError():
                logging.error("READ error: %r", rr)
            else:
                logging.info("READ ok: HR[%d..%d] = %s",
                             args.addr, args.addr + args.count - 1, rr.registers)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info("Stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()