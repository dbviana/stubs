"""
dummy_server

For testing stub
"""


import argparse
from ipaddress import ip_address
import socket
import struct
import threading


class ClientThread(threading.Thread):
    """
    Handles communication with stub
    """

    def __init__(self, _sock, _ip, _port):
        threading.Thread.__init__(self, daemon=True)
        self.sock = _sock
        self.client_ip = _ip
        self.client_port = _port
        print("[+] New connection: {} {}".format(self.client_ip, self.client_port))

        self.unpacker = struct.Struct("I f f")
        self.exit = False

    def run(self):
        while not self.exit:
            data = self.sock.recv(self.unpacker.size)
            # print("Recv data: {}".format(data))
            if len(data) == 0:
                # Connection terminated
                print(
                    "[-] Connection terminated: {} {}".format(
                        self.client_ip, self.client_port
                    )
                )
                break

            info = self.unpacker.unpack(data)
            for val in info:
                print("{:.2f} ".format(val), end="")
            print("")

        print("[X] Closing socket: {} {}".format(self.client_ip, self.client_port))
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()


parser = argparse.ArgumentParser(
    prog="stub",
    description="Dummy server for testing the simulation of a simple EV charger.",
)
parser.add_argument("--my_addr", type=ip_address, required=True, help="my address")
parser.add_argument("--my_port", type=int, default=12345, help="my port")
args = parser.parse_args()


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(1)
sock.bind((str(args.my_addr), args.my_port))
# sock.bind((socket.get_hostname(), args.my_port))

sock.listen(5)

threads = []

CLIENT_SOCK = None
IP = None
PORT = None

try:
    while True:
        try:
            CLIENT_SOCK, (IP, PORT) = sock.accept()
        except socket.timeout:
            continue

        new_thr = ClientThread(CLIENT_SOCK, IP, PORT)
        new_thr.start()
        threads.append(new_thr)

except KeyboardInterrupt:
    print("Exiting!")

    for thr in threads:
        thr.exit = True

    sock.close()

    for thr in threads:
        thr.join(1)
