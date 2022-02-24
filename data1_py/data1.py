#!/usr/bin/env python3

import serial
import serial.tools.list_ports
import struct
from pprint import pprint
import math


def checksum(by):
    sum = 0
    for b in by:
        sum = sum + b
    nbits = 8
    val = 256 - sum
    checksum = bytearray(((val + (1 << nbits)) % (1 << nbits),))
    return checksum


def get_pressure(ser, addr=255):
    req = bytearray((0x55, addr, 0x00, 0x08, 0x05, 0x10, 0x00, 0x8F))
    ser.write(req)
    ret = ser.read(11)
    value = struct.unpack("f", ret[6:10])[0]
    return value


def delete_device_archive(ser, addr=255):
    req = bytearray((0x55, addr, 0x00, 0x0B, 0x1F, 0x22, 0x00, 0x00, 0x00, 0x00))
    req = req + checksum(req)
    ser.write(req)
    ret = ser.read(7)
    for b in ret:
        print(hex(b))


def list_serial_ports():
    SerialsList = []
    for port in serial.tools.list_ports.comports():
        SerialsList.append(port.device)
        # print(port.vid)
        # print(port.interface)
        # print(port.description)
        # print(port.device)
        # print(port.name)
    return SerialsList


def connect_serial(port="COM4"):
    print("Connecting to serial port {}".format(port))
    ser = serial.Serial(port=port, baudrate=9600, parity=serial.PARITY_EVEN, timeout=1)
    return ser


# gets number of samples stored in memory
def get_samples_count(ser, device_addr=255):
    req = bytearray((0x55, device_addr, 0x00, 0x07, 0x1E, 0x22))
    req = req + checksum(req)
    pprint(req)
    ser.write(req)
    ret = ser.read(11)
    samples = struct.unpack("f", ret[6:10])[0]
    print(samples)
    return samples


def read_archive(ser):
    archive = []
    samples_available = get_samples_count(ser)
    segments = int(math.ceil(samples_available / 14.0))
    print("Available records: {} Segments: {}".format(samples_available, segments))
    mem_addr = 0
    seg = 0
    while seg <= segments:
        print("Reading segment {} / {}".format(seg, segments))
        archive.extend(read_bytes_from_memory(ser, mem_addr))
        mem_addr = mem_addr + 140
        seg = seg + 1
    return archive


def read_bytes_from_memory(ser, mem_addr, device_addr=255):
    records = []
    archive = []
    mem_addr_bytes = struct.pack("<f", mem_addr)
    req = bytearray((0x55, device_addr, 0x00, 0x0B, 0x1E, 0x23)) + bytearray(
        mem_addr_bytes
    )
    # req = req + bytearray((0x78,)) # 00 a0 03 45 = 2106
    req = req + checksum(req)
    ser.write(req)
    ret = ser.read(147)
    i = 12  # records starting on 12th byte of response

    while i < 140:
        records.append(ret[i : i + 10])
        i = i + 10
    for record in records:
        archive.append(
            {
                "time_sec": record[0],
                "time_min": record[1] >> 3,
                "time_hour": (record[1] & 0x03) << 3 | record[2] >> 5,
                "time_day": record[2] & 0x1F,
                "time_month": record[3] >> 3,
                "time_dow": record[3] & 0x07,
                "time_year": struct.unpack(">H", record[4:6])[0],
                "value": struct.unpack("<f", record[6:10])[0],
            }
        )
    return archive
