"""
dummy_server

For testing stub
"""


import argparse
from ipaddress import ip_address
import socket
import struct
from socketserver import TCPServer, BaseRequestHandler


class Stub:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port


class DummyTCPHandler(BaseRequestHandler):
    """
    A Dummy TCP Handler
    Prints to the console whatever it receives
    """

    def handle(self):
        self.unpacker = struct.Struct("I f")
        self.data = self.request.recv(self.unpacker.size)
        print("{} wrote:".format(self.client_address[1]))

        try:
            info = self.unpacker.unpack(self.data)
            print(info)
        except Exception as e:
            print(e)

        self.request.sendall(bytes("Ok", "ascii"))
        self.request.


parser = argparse.ArgumentParser(
    prog="stub", description="Simulate a simple stateful EV charger."
)
parser.add_argument("--my_addr", type=ip_address, required=True, help="my address")
parser.add_argument("--my_port", type=int, default=12345, help="my port")
args = parser.parse_args()


class MyTCPServer(TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)


server = MyTCPServer((str(args.my_addr), args.my_port), DummyTCPHandler)

try:
    server.serve_forever()
except KeyboardInterrupt:
    server.shutdown()
