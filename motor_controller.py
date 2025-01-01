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

    def execute_command(self, command_name, value):
        """Executes a predefined command with the given value."""
        command = self.COMMANDS.get(command_name)
        if command:
            self.write_to_register(
                address=command["address"],
                value=value,
                multiplier=command.get("multiplier", 1),
                max_register_value=command.get("max_register_value")
            )
        else:
            logging.error(f"Invalid command name: {command_name}")

    def read_motor_data(self, data_type):
        """Reads motor parameters such as RPM, temperature, and voltage."""
        parameter_config = {
            "motor_temp": {"address": 261, "multiplier": 1},
            "controller_temp": {"address": 259, "multiplier": 1},
            "battery_voltage": {"address": 265, "multiplier": 0.03},
            "battery_state of charge": {"address": 267, "multiplier": 1},
            "motor_rpm": {"address": 263, "multiplier": 1},
        }

        config = parameter_config.get(data_type)
        if not config:
            logging.error(f"Invalid data type requested: {data_type}")
            return None
        try:
            raw_value = self.motor.read_register(config["address"], 0)
            scaled_value = raw_value * config["multiplier"]
            return scaled_value
        except Exception as e:
            logging.error(f"Error reading {data_type}: {e}")
            return None

    def get_last_cycle_count(self, file_name):
        """Reads the last recorded cycle count from the file."""
        if not os.path.exists(file_name):
            return 1
        try:
            with open(file_name, "r") as file:
                lines = file.readlines()
                for line in reversed(lines):
                    if line.startswith("No of cycles:"):
                        try:
                            return int(line.split(":")[1].strip())
                        except ValueError:
                            continue
        except Exception as e:
            logging.error(f"Error reading cycle count: {e}")
            return 1