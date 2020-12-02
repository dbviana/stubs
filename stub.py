"""
Stub

Simulate a simple stateful EV charger
"""

import argparse
import socket
from ipaddress import ip_address


parser = argparse.ArgumentParser(
    prog="stub", description="Simulate a simple stateful EV charger."
)
parser.add_argument(
    "--server_addr", type=ip_address, required=True, help="server address"
)
parser.add_argument("--server_port", type=ip_address, default=12345, help="server port")
args = parser.parse_args()

print(args.server_addr)

sock = socket.socket()
sock.connect((str(args.server_addr), args.server_port))
