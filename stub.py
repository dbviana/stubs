"""
Stub

Simulate a simple stateful EV charger
"""


import argparse
from ipaddress import ip_address
import socket
import struct
import time


parser = argparse.ArgumentParser(
    prog="stub", description="Simulate a simple stateful EV charger."
)
parser.add_argument(
    "--server_addr", type=ip_address, required=True, help="server address"
)
parser.add_argument("--server_port", type=ip_address, default=12345, help="server port")
args = parser.parse_args()

print(args.server_addr)


class Stub:
    def __init__(
        self, id, cap=6.1, perc=0.2, falloff=0.7, min_power=5, max_power=62.5,
    ):
        self.id = id
        self.battery_capacity = cap
        self.perc = perc
        self.current_battery = perc * cap

        self.falloff_point = falloff
        self.min_power = min_power
        self.max_power = max_power

        self.charging = False
        self.power_intake = None
        self.available_power = None

        self._init_socket()

    def _init_socket(self):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect((str(args.server_addr), args.server_port))

    def start_charging_at(self, available_power):
        self.charging = True
        self.available_power = available_power

        self._calculate_power_intake()

    def _calculate_power_intake(self):
        def lerp_power(perc):
            return self.max_power + perc * (self.min_power - self.max_power)

        if self.perc < self.falloff_point:
            self.power_intake = min(self.max_power, self.available_power)
        else:
            self.power_intake = min(lerp_power(self.perc), self.available_power)

    def charge(self, delta_t):
        """
        Simple charge curve
        Charges at full speed until a certain
        percentage point, from which charging
        speeds decay linearly until a minimum
        charging speed at 100%. Must also take
        into account the available power.
        """

        self._calculate_power_intake()
        self.current_battery += self.power_intake * delta_t
        self.perc = self.current_battery / self.battery_capacity

        if self.perc >= 1:
            self.perc = 1
            self.current_battery = self.battery_capacity
            self.charging = 0

    def inform_server(self):
        values = (self.id, self.power_intake)
        packer = struct.Struct("I f")
        packed_data = packer.pack(*values)

        try:
            print("Sending packet... (ID:{}, {}kWh)".format(*values))
            self.sock.send(packed_data)
        except ConnectionAbortedError:
            pass

        self.sock.close()
        self._init_socket()

    def __repr__(self):
        s = "Stub no. {}: ".format(self.id)

        if self.charging:
            s += "Charging @{:.2f}kWh ".format(self.power_intake)
        else:
            s += "Idle "

        s += "({:.2f}/{:.2f}kWh [{:.2f}%])".format(
            self.current_battery, self.battery_capacity, self.perc * 100
        )

        return s


# sock.sendall(b"abcde")
# buf = sock.recv(64)

stub0 = Stub(0)

stub0.start_charging_at(100)

time_speed = 100
time_sleep = 0.1

while stub0.charging:
    print(stub0)
    stub0.charge(time_sleep * time_speed / 3600)
    stub0.inform_server()
    time.sleep(time_sleep)
