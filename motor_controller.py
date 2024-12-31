import minimalmodbus
import serial
import logging
import os
import time

logging.basicConfig(
    filename="Log_no_of_cycles.log",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


class MotorController:
    def __init__(self, port='COM4', slave_address=1, baudrate=115200):
        self.motor = None
        self.port = port
        self.slave_address = slave_address
        self.baudrate = baudrate
        self.running = False
        self.setup_motor()

    def setup_motor(self):
        """Configures the motor's Modbus connection."""
        self.motor = minimalmodbus.Instrument(self.port, self.slave_address)
        self.motor.serial.baudrate = self.baudrate
        self.motor.serial.bytesize = 8
        self.motor.serial.parity = serial.PARITY_NONE
        self.motor.serial.stopbits = 1
        self.motor.serial.timeout = 1
        return self.motor

    def write_to_register(self, address, value, multiplier=1, max_register_value=None):
        """Writes a value to a specified Modbus register with optional processing."""
        value = int(value * multiplier)
        if max_register_value and value < 0:
            value = max_register_value + value
        self.motor.write_registers(address, [value])
        logging.info(f"Successfully wrote {value} to address {address}")

    COMMANDS = {
        "set_speed_regulator_mode": {"address": 11},
        "set_remote_torque_command": {"address": 494, "multiplier": 40.46, "max_register_value": 2 ** 16},
        "set_remote_maximum_regen_battery_current_limit": {"address": 361, "multiplier": 8},
        "set_remote_maximum_battery_current_limit": {"address": 360, "multiplier": 8},
        "set_remote_maximum_motoring_current": {"address": 491, "multiplier": 40.96},
        "set_remote_maximum_braking_current": {"address": 492, "multiplier": 40.96},
        "set_remote_maximum_braking_torque": {"address": 1680, "multiplier": 40.96},
        "set_remote_speed_command": {"address": 1677, "max_register_value": 2 ** 16},
        "set_remote_state_command": {"address": 493},
    }