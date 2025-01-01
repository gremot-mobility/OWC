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

    def calculate_battery_soc(self, battery_voltage):
        """
        Calculates the battery State of Charge (SOC) based on battery voltage.
        """
        if battery_voltage >= 48:
            return 1.0
        elif battery_voltage <= 30:
            return 0.0
        else:
            return (battery_voltage - 30) / (48 - 30)

    def check_one_way_clutch(self, torque_duration_pairs):
        """
        Check for one-way clutch wear-out during reverse torque conditions.
        """
        for torque, duration in torque_duration_pairs:
            if torque < 0:
                self.execute_command("set_remote_torque_command", torque)
                time.sleep(duration)
                motor_rpm = self.read_motor_data("motor_rpm")
                if motor_rpm < 0:
                    logging.warning("One-way clutch might be worn out. Negative RPM detected.")
                    return False
        return True

    def cooldown_motor(self):
        """
        Cool down the motor when the temperature exceeds the threshold.
        """
        motor_temp = self.read_motor_data("motor_temp")
        logging.warning("Motor temperature exceeds threshold. Cooling before retry.")
        while motor_temp > 30:
            time.sleep(600)
            motor_temp = self.read_motor_data("motor_temp")

    def check_battery_soc(self):
        """
        Ensure battery SOC remains above the threshold.
        """
        battery_soc = self.read_motor_data("battery_state of charge")
        if battery_soc < 30:
            logging.warning("Battery SOC below threshold. Cooling before retry.")
            time.sleep(300)
            return False
        return True

    def perform_motor_cycles(self, torque_duration_pairs, cycle_count_target, txt_file_name):
        """Performs motorcycles and logs the data."""
        try:
            # Get current cycle count
            current_count = self.get_last_cycle_count(txt_file_name) or 1

            # Calculate target count
            if cycle_count_target == -1:
                target_count = float('inf')
            else:
                target_count = current_count + cycle_count_target

            while current_count < target_count and self.running:
                try:
                    # Battery check with retry
                    retry_count = 0
                    while retry_count < 3:  # Try up to 3 times
                        try:
                            if not self.check_battery_soc():
                                time.sleep(1)
                                retry_count += 1
                                continue
                            break
                        except (minimalmodbus.InvalidResponseError, serial.SerialTimeoutException):
                            time.sleep(1)
                            retry_count += 1
                    if retry_count == 3:
                        logging.error("Failed to check battery after 3 retries")
                        continue

                    # Temperature check with retry
                    motor_temp = self.read_motor_data("motor_temp")
                    if motor_temp and motor_temp > 90:
                        self.cooldown_motor()
                        continue

                    # Execute each torque-duration pair
                    forward_torque = None
                    reverse_torque = None
                    negative_torque = None

                    for torque, duration in torque_duration_pairs:
                        if not self.running:
                            break

                        # Set torque with retry
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                self.execute_command("set_remote_torque_command", torque)
                                break
                            except (minimalmodbus.InvalidResponseError, serial.SerialTimeoutException):
                                time.sleep(1)
                                retry_count += 1
                        if retry_count == 3:
                            logging.error(f"Failed to set torque {torque} after 3 retries")
                            continue

                        # Wait for duration
                        start_time = time.time()
                        while time.time() - start_time < duration and self.running:
                            time.sleep(0.1)

                        # Read motor RPM with retry
                        retry_count = 0
                        while retry_count < 3:
                            try:
                                motor_rpm = self.read_motor_data("motor_rpm")
                                if motor_rpm is not None:
                                    if torque > 0:
                                        forward_torque = motor_rpm
                                    elif torque == 0:
                                        reverse_torque = motor_rpm
                                    elif torque < -1:
                                        negative_torque = motor_rpm
                                break
                            except (minimalmodbus.InvalidResponseError, serial.SerialTimeoutException):
                                time.sleep(1)
                                retry_count += 1

                    if not self.running:
                        break

                    retry_count = 0
                    while retry_count < 3:
                        try:
                            motor_temp = self.read_motor_data("motor_temp")
                            controller_temp = self.read_motor_data("controller_temp")
                            battery_voltage = self.read_motor_data("battery_voltage")
                            if all(v is not None for v in [motor_temp, controller_temp, battery_voltage]):
                                break
                        except (minimalmodbus.InvalidResponseError, serial.SerialTimeoutException):
                            time.sleep(1)
                            retry_count += 1

                    # Log cycle data
                    cycle_data = (
                        f"No of cycles: {current_count}\n"
                        f"Set RPM: 320 RPM\n"
                        f"Motor RPM in forward torque: {forward_torque} RPM\n"
                        f"Motor Temperature: {motor_temp} degC\n"
                        f"Controller Temperature: {controller_temp} degC\n"
                        f"Battery Voltage: {battery_voltage:.3f} V\n"
                        f"Motor RPM in reverse torque: {reverse_torque} RPM\n"
                        f"Motor RPM in negative torque: {negative_torque} RPM\n\n"
                    )

                    # Write cycle data
                    try:
                        with open(txt_file_name, "a") as txt_file:
                            txt_file.write(cycle_data)
                        logging.info(f"Cycle {current_count} logged successfully")
                    except Exception as e:
                        logging.error(f"Error writing to file: {e}")

                    current_count += 1
                    logging.info(
                        f"Completed cycle {current_count} of {target_count if cycle_count_target != -1 else 'continuous'}")

                    # Check if target reached
                    if cycle_count_target != -1 and current_count >= target_count:
                        logging.info("Target cycles completed")
                        self.running = False
                        break

                except Exception as e:
                    logging.error(f"Error during cycle execution: {e}")
                    time.sleep(1)  # Wait before retrying
                    continue

        except Exception as e:
            logging.error(f"Critical error in perform_motor_cycles: {e}")
        finally:
            # Ensure motor is stopped
            try:
                self.execute_command("set_remote_torque_command", 0)
                self.execute_command("set_remote_state_command", 0)
            except Exception as e:
                logging.error(f"Error stopping motor: {e}")

        return current_count

    def start_test(self, params, cycle_count_target=-1):
        """Starts the motor test with the given parameters."""
        try:
            self.running = True
            self.execute_command("set_speed_regulator_mode", 2)
            self.execute_command("set_remote_torque_command", params["forward_torque"])
            self.execute_command("set_remote_maximum_regen_battery_current_limit", 41)
            self.execute_command("set_remote_maximum_battery_current_limit", 70)
            self.execute_command("set_remote_maximum_motoring_current", params["max_motor_current"])
            self.execute_command("set_remote_maximum_braking_current", params["max_brake_current"])
            self.execute_command("set_remote_maximum_braking_torque", abs(params["reverse_torque"]))
            self.execute_command("set_remote_speed_command", params["target_rpm"])
            self.execute_command("set_remote_state_command", 2)

            torque_duration_pairs = [
                (params["forward_torque"], params["forward_duration"]),
                (params["reverse_torque"], params["reverse_duration"])
            ]
            return self.perform_motor_cycles(torque_duration_pairs, cycle_count_target, "No_of_cycles.txt")
        except Exception as e:
            logging.error(f"Error starting test: {e}")
            self.stop_test()
            raise

    def stop_test(self):
        """Stops the motor test."""
        self.running = False
        try:
            self.execute_command("set_remote_torque_command", 0)
            self.execute_command("set_remote_state_command", 0)
            logging.info("Motor stopped")
        except Exception as e:
            logging.error(f"Error stopping motor: {e}")
            raise
