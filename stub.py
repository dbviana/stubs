"""
Stub

Simulate a simple stateful EV charger
"""


import argparse
from ipaddress import ip_address
import socket
import time
import datetime

import common

RECEIVE_TIMEOUT = 999


parser = argparse.ArgumentParser(
    prog="stub", description="Simulate a simple EV charger."
)
parser.add_argument("--id", type=int, required=True, help="stub id")
parser.add_argument(
    "--server_addr", type=ip_address, required=True, help="server address"
)
parser.add_argument("--server_port", type=ip_address, default=5050, help="server port")
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

        # power must be converted to W
        self.min_power = power_bounds[0] * 1000
        self.max_power = power_bounds[1] * 1000

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

        delta_t in seconds and power_intake in Watts
        """

        # Convert to kWh from Ws
        self.current_battery += (power_intake / 1000) * (delta_t / 3600)
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
        # self.identifier = int(str(datetime.datetime.now().year) + str(ID).zfill(2))
        # Actually, hardcode the year
        self.identifier = int(str(2020) + str(ID).zfill(2))
        self.battery = battery

        self.charging = False
        self.charging_mode = None
        self.power_intake = None
        self.available_power = None

        self._init_socket()

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((str(args.server_addr), args.server_port))

    def start_charging_at(self, available_power, charging_mode):
        """
        Sets up charging info
        """
        self.charging = True
        self.charging_mode = charging_mode
        self.available_power = available_power
        self.calculate_power_intake()

    def stop_charging(self):
        self.charging = False
        self.available_power = 0
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
        Simulate charging the battery,
        handles battery being full
        """

        self.calculate_power_intake()
        self.battery.charge(delta_t, self.power_intake)
        if self.battery.perc == 1.0:
            self.charging = 0

    def say_hello_to_server(self):
        base_packet = {
            "module": "stub",
            "chargerID": self.identifier,
            "stateOccupation": 0,
            "newConnection": 1,
            "chargingMode": 2,  # Not charging, TODO: Add fast charging mode
            "voltageMode": 0,  # TODO: Add AC charging
            "instPower": 0,
            "maxPower": 0,
            "voltage": 400,
        }
        common.send_json_message(self.sock, base_packet)

    def interpret_message(self, _json_msg):
        if _json_msg["chargerID"] != self.identifier:
            print(
                "[!] Is this packet for us? I'm not Stub no. {}, I'm no. {}. Ignoring.".format(
                    _json_msg["chargerID"], self.identifier
                )
            )
            return

        if _json_msg["chargingMode"] == 0:
            self.start_charging_at(_json_msg["maxPower"], _json_msg["chargingMode"])

        # TODO: Handle fast charging

        if _json_msg["chargingMode"] == 2:  # Stop charging
            if self.charging:
                self.stop_charging()

    def send_charge_data(self):
        charging_mode = 2
        if self.charging:
            charging_mode = 0

        _json_data = {
            "module": "stub",
            "chargerID": self.identifier,
            "stateOccupation": 1,
            "newConnection": 0,
            "chargingMode": charging_mode,  # 0 = Normal Speed # TODO: Add fast charging mode
            "voltageMode": 0,  # TODO: Add AC charging
            "instPower": self.power_intake,
            "maxPower": self.available_power,
            "voltage": 400,
        }
        # print("Sent message {}".format(_json_data))
        common.send_json_message(self.sock, _json_data)

        try:
            _json_data = common.receive_json_message(self.sock, timeout=RECEIVE_TIMEOUT)
            self.interpret_message(_json_data)
        except TimeoutError:
            print("[!] Server may be down? It's not replying.")

    def stop_charging_battery_full(self):
        """
        Inform server that charging has
        stopped due to a full battery
        """
        json_data = {
            "module": "stub",
            "chargerID": self.identifier,
            "stateOccupation": 1,
            "newConnection": 0,
            "chargingMode": 2,  # Off
            "voltageMode": 0,  # Assume DC TODO: Don't
            "instPower": 0,
            "maxPower": 0,
            "voltage": 400,
        }
        common.send_json_message(self.sock, json_data)

    def disconnect(self):
        """
        Inform server that charging has
        stopped due to a manual disconnect
        """
        json_data = {
            "module": "disconnected",
            "chargerID": self.identifier,
            "stateOccupation": 0,
            "newConnection": 0,
            "chargingMode": 2,  # Off
            "voltageMode": 0,  # Assume DC TODO: Don't
            "instPower": 0,
            "maxPower": 0,
            "voltage": 400,
        }
        common.send_json_message(self.sock, json_data)

        self.raw_disconnect()

    def raw_disconnect(self):
        """
        Disconnects from the server
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


stub0 = Stub(args.id)

TIME_SPEED = 30
TIME_SLEEP = 1
TIME_ELAPSED = 0
TIME_UNTIL_DISCONNECT = 9999

while True:
    try:
        # Introduce myself and await
        stub0.say_hello_to_server()
        json_msg = common.receive_json_message(stub0.sock, timeout=20)

        if json_msg["chargingMode"] != 2:
            stub0.start_charging_at(json_msg["maxPower"], json_msg["chargingMode"])
            break

    except TimeoutError:
        continue

# Finished introducing myself,
# onto normal operation

while True:
    print(stub0)

    # Simulation loop

    try:
        stub0.send_charge_data()
    except Exception as e:
        print("[!] Server must be down: exiting!", e)
        break

    try:
        time.sleep(TIME_SLEEP)
        TIME_ELAPSED += TIME_SLEEP
    except Exception:
        print("[!] Exception received: exiting!")
        break

    stub0.charge(TIME_SLEEP * TIME_SPEED)  # in seconds

    if TIME_ELAPSED > TIME_UNTIL_DISCONNECT:
        break

stub0.disconnect()
