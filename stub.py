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
    prog="stub", description="Simulate a simple EV charger."
)
parser.add_argument(
    "--server_addr", type=ip_address, required=True, help="server address"
)
parser.add_argument("--server_port", type=ip_address, default=12345, help="server port")
args = parser.parse_args()

print(args.server_addr)


class Battery:
    """
    Encapsulates the characteristics and
    behavior of an EV battery
    """

    def __init__(self, cap, perc, falloff, power_bounds):
        self.battery_capacity = cap
        self.perc = perc
        self.current_battery = perc * cap

        self.falloff_point = falloff
        self.min_power = power_bounds[0]
        self.max_power = power_bounds[1]

    def calculate_max_power_intake(self):
        """
        Calculates max power intake at a certain battery
        level
        """

        if self.perc < self.falloff_point:
            return self.max_power

        return self.max_power + self.perc * (self.min_power - self.max_power)

    def charge(self, delta_t, power_intake):
        """
        Simple charge curve
        Charges at full speed until a certain
        percentage point, from which charging
        speeds decay linearly until a minimum
        charging speed at 100%. Must also take
        into account the available power.
        """
        self.current_battery += power_intake * delta_t
        self.perc = self.current_battery / self.battery_capacity

        if self.perc >= 1:
            self.perc = 1
            self.current_battery = self.battery_capacity

    def __repr__(self):
        return "({:.2f}/{:.2f}kWh [{:.2f}%])".format(
            self.current_battery, self.battery_capacity, self.perc * 100
        )


default_battery = Battery(cap=6.1, perc=0.2, falloff=0.7, power_bounds=(5, 62.5))


class Stub:
    """
    Simulates a single charger unit
    """

    def __init__(self, ID, battery=default_battery):
        self.identifier = ID
        self.battery = battery

        self.charging = False
        self.power_intake = None
        self.available_power = None

        self.packer = struct.Struct("I f f")

        self._init_socket()

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(args.server_addr), args.server_port))

    def start_charging_at(self, available_power):
        """
        Sets up charging info
        """
        self.charging = True
        self.available_power = available_power
        self.calculate_power_intake()

    def calculate_power_intake(self):
        """
        Calculates power intake given the current
        available power and battery level
        """
        self.power_intake = min(
            self.battery.calculate_max_power_intake(), self.available_power
        )

    def charge(self, delta_t):
        """
        Simulate charging the battery
        """

        self.calculate_power_intake()
        self.battery.charge(delta_t, self.power_intake)
        if self.battery.perc == 1.0:
            self.charging = 0

    def inform_server(self):
        """
        Informs the server of the stub's
        current status
        """
        values = (self.identifier, self.power_intake, self.battery.perc * 100)
        packed_data = self.packer.pack(*values)

        # print("Sending packet... (identifier:{}, {:.2f}kWh, {:.2f}%)".format(*values))
        self.sock.send(packed_data)

    def disconnect(self):
        """
        Disconnects from the server and
        cleans up
        """
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def __repr__(self):
        return (
            "Stub no. {}: ".format(self.identifier)
            + str(self.battery)
            + (
                " Charging @{:.2f}kWh".format(self.power_intake)
                if self.charging
                else " Idle"
            )
        )


stub0 = Stub(0)

stub0.start_charging_at(100)

TIME_SPEED = 100
TIME_SLEEP = 1
TIME_ELAPSED = 0

while True:
    print(stub0)

    try:
        stub0.inform_server()
    except ConnectionAbortedError:
        print("[!] Server must be down: exiting!")
        break

    time.sleep(TIME_SLEEP)
    TIME_ELAPSED += TIME_SLEEP

    stub0.charge(TIME_SLEEP * TIME_SPEED / 3600)

    if TIME_ELAPSED > 10:
        break


stub0.disconnect()
