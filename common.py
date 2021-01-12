import socket
import json
import struct


def receive_json_message(sock, timeout=None):
    sock.settimeout(timeout)

    try:
        data = sock.recv(struct.Struct("I").size)
        if len(data) == 0:
            return None

        size = struct.Struct("I").unpack(data)

        data = sock.recv(size[0])
        if len(data) == 0:
            return None

        json_data = json.loads(data.decode("utf-8"))
        # print(json_data)
        return json_data
    except TimeoutError:
        print("Timeout!")
        return None


def send_json_message(sock, json_data):
    data = json.dumps(json_data)
    data_size = len(data.encode("utf-8"))
    header = struct.pack("I", data_size)

    # print("Sending packet... (identifier:{}, {:.2f}kWh, {:.2f}%)".format(*values))
    sock.send(header)
    sock.send(bytes(data, "utf-8"))
