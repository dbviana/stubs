"""
dummy_server

For testing stub
"""


import argparse
from ipaddress import ip_address
import socket
import struct
import threading

import common


class ClientThread(threading.Thread):
    """
    Handles communication with stub
    """

    def __init__(self, _sock, _ip, _port):
        threading.Thread.__init__(self, daemon=True)
        self.sock = _sock
        self.client_ip = _ip
        self.client_port = _port
        self.id = None
        print("[+] New connection: {} {}".format(self.client_ip, self.client_port))

        self.unpacker = struct.Struct("!I")
        self.exit = False

    def interpret_message(self, _json_msg):
        if self.id is None:
            self.id = _json_msg["chargerID"]
        elif self.id != _json_msg["chargerID"]:
            print(
                "[X] ERROR: Different charger id on the same socket? Shouldn't happen! Got {}, expected {}.",
                _json_msg["chargerID"],
                self.id,
            )

        # Interpreting starts here

        if _json_msg["newConnection"]:
            print(
                "[!] {} ({}:{}) wants to start charging!".format(
                    self.id, self.client_ip, self.client_port
                )
            )

            _json_msg["chargingMode"] = 0
            _json_msg["maxPower"] = 60

            common.send_json_message(self.sock, _json_msg)
            print(
                "[<] Authorizing {} to charging a maximum of {}kWh.".format(
                    self.id, _json_msg["maxPower"]
                )
            )
            return

        if _json_msg["chargingMode"] == 0:
            print(
                "[>] {} is charging at {:.2f}kWh (from the {:.2f}kWh available to it).".format(
                    self.id, _json_msg["instPower"], _json_msg["maxPower"]
                )
            )

            common.send_json_message(self.sock, _json_msg)
            return

        if _json_msg["chargingMode"] == 2:
            if _json_msg["stateOccupation"] == 0:
                print("[!] {} disconnected.".format(self.id))
            elif _json_msg["stateOccupation"] == 1:
                print("[!] {} is done charging.".format(self.id))
                common.send_json_message(self.sock, _json_msg)

            return

        print("[!] Got {}. Message not handled!".format(_json_msg))

    def run(self):
        while not self.exit:
            # print("Waiting for message...")
            json_msg = common.receive_json_message(self.sock)
            # print(json_msg)
            if json_msg is None:
                break

            self.interpret_message(json_msg)

            # if json_msg["stateOccupation"] == 0:
            #    break

        print("[X] Closing socket: {} {}".format(self.client_ip, self.client_port))
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()


parser = argparse.ArgumentParser(
    prog="stub",
    description="Dummy server for testing the simulation of a simple EV charger.",
)
parser.add_argument("--my_addr", type=ip_address, required=True, help="my address")
parser.add_argument("--my_port", type=int, default=5050, help="my port")
args = parser.parse_args()


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(1)

bind_args = (str(args.my_addr), args.my_port)
sock.bind(bind_args)
print(bind_args)

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
