"""
dummy_server

For testing stub
"""

import argparse
from socketserver import TCPServer, BaseRequestHandler
from ipaddress import ip_address


class DummyTCPHandler(BaseRequestHandler):
    """
    A Dummy TCP Handler
    Prints to the console whatever it receives
    """

    def handle(self):
        self.data = self.request.recv(1024).strip()
        print("{} wrote:".format(self.client_address[0]))
        print(self.data)


parser = argparse.ArgumentParser(
    prog="stub", description="Simulate a simple stateful EV charger."
)
parser.add_argument("--my_addr", type=ip_address, required=True, help="my address")
parser.add_argument("--my_port", type=int, default=12345, help="my port")
args = parser.parse_args()

with TCPServer((str(args.my_addr), args.my_port), DummyTCPHandler) as server:
    server.serve_forever()
