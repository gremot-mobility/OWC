import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
from motor_controller import MotorController


class OneWayClutchTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("One-Way Clutch Tester")
        self.root.geometry("1000x800")
        # Initialize variables
        self.init_variables()
        # Create GUI elements
        self.create_gui()
        # Start parameter updates
        self.root.after(1000, self.update_parameters)
        try:
            self.motor_controller = MotorController()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize motor controller: {str(e)}")
            self.motor_controller = None


    def init_variables(self):
        """Initialize all GUI variables"""
        self.target_cycles = tk.StringVar(value="-1")
        self.running = False
        self.current_cycle = tk.StringVar(value="0")
        self.motor_rpm = tk.StringVar(value="0")
        self.motor_torque = tk.StringVar(value="0")
        self.controller_temp = tk.StringVar(value="0")
        self.motor_temp = tk.StringVar(value="0")
        self.battery_soc = tk.StringVar(value="0")
        self.battery_voltage = tk.StringVar(value="0")
        self.status_message = tk.StringVar(value="System Ready")

        # Control parameters
        self.target_rpm = tk.StringVar(value="320")
        self.forward_torque = tk.StringVar(value="100")
        self.reverse_torque = tk.StringVar(value="-100")
        self.forward_duration = tk.StringVar(value="5")
        self.reverse_duration = tk.StringVar(value="3")
        self.max_motor_current = tk.StringVar(value="100")
        self.max_brake_current = tk.StringVar(value="100")

    def create_gui(self):
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        try:
            logo_path = r"C:\Users\Rakshith K\Desktop\OWC\download.png"
            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((300, 200))
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(main_container, image=self.logo_photo)
            logo_label.pack(pady=1)
        except Exception as e:
            print(f"Error loading logo: {e}")
        title_label = tk.Label(main_container, text="One-Way Clutch Tester", font=("Arial", 35, "bold"))
        title_label.place(x=510, y=135)

        # Parameters Frame with three columns
        params_frame = tk.Frame(main_container)
        params_frame.pack(fill="x", pady=5)

        # Motor Parameters
        motor_frame = tk.LabelFrame(params_frame, text="Motor Parameters", height=150)
        motor_frame.pack(side="left", padx=5, fill="both", expand=True)
        motor_frame.pack_propagate(False)

        self.create_param_row(motor_frame, "Motor RPM:", self.motor_rpm, "RPM", readonly=True)
        self.create_param_row(motor_frame, "Motor Torque:", self.motor_torque, "Nm", readonly=True)

        # Controller Parameters
        controller_frame = tk.LabelFrame(params_frame, text="Controller Parameters", height=150)
        controller_frame.pack(side="left", padx=5, fill="both", expand=True)
        controller_frame.pack_propagate(False)

        self.create_param_row(controller_frame, "Controller Temp:", self.controller_temp, "°C", readonly=True)
        self.create_param_row(controller_frame, "Motor Temp:", self.motor_temp, "°C", readonly=True)

        # Battery Parameters
        battery_frame = tk.LabelFrame(params_frame, text="Battery Parameters", height=150)
        battery_frame.pack(side="left", padx=5, fill="both", expand=True)
        battery_frame.pack_propagate(False)

        self.create_param_row(battery_frame, "Battery SOC:", self.battery_soc, "%", readonly=True)
        self.create_param_row(battery_frame, "Battery Voltage:", self.battery_voltage, "V", readonly=True)

        # Control Parameters Frame
        control_params_frame = tk.LabelFrame(main_container, text="Control Parameters")
        control_params_frame.pack(fill="x", pady=10, padx=5)

        # Create two columns for control parameters
        left_control = tk.Frame(control_params_frame)
        left_control.pack(side="left", fill="both", expand=True, padx=5)

        right_control = tk.Frame(control_params_frame)
        right_control.pack(side="left", fill="both", expand=True, padx=5)

        # Left column parameters
        self.create_param_row(left_control, "Target RPM:", self.target_rpm, "RPM")
        self.create_param_row(left_control, "Forward Torque:", self.forward_torque, "%")
        self.create_param_row(left_control, "Forward Duration:", self.forward_duration, "sec")

        # Right column parameters
        self.create_param_row(right_control, "Max Motor Current:", self.max_motor_current, "A")
        self.create_param_row(right_control, "Reverse Torque:", self.reverse_torque, "%")
        self.create_param_row(right_control, "Reverse Duration:", self.reverse_duration, "sec")

        # Cycles Frame
        cycles_frame = tk.Frame(main_container)
        cycles_frame.pack(fill="x", pady=10)

        tk.Label(cycles_frame, text="Target Cycles (-1 for continuous):", font=("Arial", 10, "bold")).pack(
            side="left", padx=5)
        target_cycles_entry = tk.Entry(cycles_frame, textvariable=self.target_cycles, width=10)
        target_cycles_entry.pack(side="left", padx=5)

        tk.Label(cycles_frame, text="Total Number of Cycles Completed:", font=("Arial", 10, "bold")).pack(
            side="left",
            padx=5)
        tk.Entry(cycles_frame, textvariable=self.current_cycle, state="readonly", width=10).pack(side="left")

        # Control Buttons
        button_frame = tk.Frame(main_container)
        button_frame.pack(pady=10)

        self.start_button = tk.Button(button_frame, text="Start", command=self.start_test, width=15)
        self.start_button.pack(side="left", padx=10)

        self.stop_button = tk.Button(button_frame, text="Stop", command=self.stop_test, width=15)
        self.stop_button.pack(side="left", padx=10)

        # Status Frame
        status_frame = tk.Frame(main_container)
        status_frame.pack(fill="x", pady=5)

        # Status lights
        lights_frame = tk.Frame(status_frame)
        lights_frame.pack()

        self.create_status_lights(lights_frame)

        # Status message
        message_frame = tk.LabelFrame(status_frame, text="Status Message")
        message_frame.pack(fill="x", padx=20, pady=10)
        tk.Label(message_frame, textvariable=self.status_message).pack(pady=5)
