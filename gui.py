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

    def create_param_row(self, parent, label_text, variable, unit, readonly=False):
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=2)

        tk.Label(frame, text=label_text, width=15, anchor="e").pack(side="left", padx=2)
        tk.Entry(frame, textvariable=variable, width=8,
                 state="readonly" if readonly else "normal").pack(side="left", padx=2)
        tk.Label(frame, text=unit, width=4, anchor="w").pack(side="left")

    def create_status_lights(self, parent):
        self.canvas_red = tk.Canvas(parent, width=30, height=30)
        self.canvas_yellow = tk.Canvas(parent, width=30, height=30)
        self.canvas_green = tk.Canvas(parent, width=30, height=30)

        self.canvas_red.pack(side="left", padx=5)
        self.canvas_yellow.pack(side="left", padx=5)
        self.canvas_green.pack(side="left", padx=5)

        self.update_status_lights("ready")

    def update_status_lights(self, status):
        """Updates status lights based on system state"""
        # Clear all lights
        for canvas in [self.canvas_red, self.canvas_yellow, self.canvas_green]:
            canvas.delete("all")
            canvas.create_oval(5, 5, 25, 25, fill="grey")

        if status == "running":
            self.canvas_green.delete("all")
            self.canvas_green.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("Motor is Running")
        elif status == "warning":
            self.canvas_yellow.delete("all")
            self.canvas_yellow.create_oval(5, 5, 25, 25, fill="yellow")
            self.status_message.set("Warning: Check Parameters")
        elif status == "stopped":
            self.canvas_red.delete("all")
            self.canvas_red.create_oval(5, 5, 25, 25, fill="red")
            self.status_message.set("System Stopped")
        elif status == "completed":
            # Flash all lights green to indicate successful completion
            for canvas in [self.canvas_red, self.canvas_yellow, self.canvas_green]:
                canvas.delete("all")
                canvas.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("Target Cycles Completed Successfully")
        else:  # ready
            self.canvas_green.delete("all")
            self.canvas_green.create_oval(5, 5, 25, 25, fill="green")
            self.status_message.set("System Ready")

    def update_parameters(self):
        """Updates all GUI parameters with current motor values"""
        try:
            if self.running and self.motor_controller:
                try:
                    self.motor_rpm.set(str(self.motor_controller.read_motor_data("motor_rpm") or 0))
                    self.motor_temp.set(str(self.motor_controller.read_motor_data("motor_temp") or 0))
                    self.controller_temp.set(str(self.motor_controller.read_motor_data("controller_temp") or 0))
                    self.battery_voltage.set(f"{self.motor_controller.read_motor_data('battery_voltage') or 0:.1f}")
                    self.battery_soc.set(str(self.motor_controller.read_motor_data("battery_state of charge") or 0))

                    # Update cycle count
                    current_count = self.motor_controller.get_last_cycle_count("No_of_cycles.txt")
                    self.current_cycle.set(str(current_count))

                    # Check warning conditions
                    if float(self.motor_temp.get()) > 80:
                        self.update_status_lights("warning")
                    elif float(self.battery_soc.get()) < 30:
                        self.update_status_lights("warning")
                    else:
                        self.update_status_lights("running")

                except Exception as e:
                    print(f"Error reading motor data: {e}")
                    self.update_status_lights("warning")

        except Exception as e:
            print(f"Error in update_parameters: {e}")

        # Schedule the next update
        self.root.after(1000, self.update_parameters)

    def start_test(self):
        """Handles the start button click"""
        if not self.running and self.motor_controller:
            try:
                target_cycles = int(self.target_cycles.get())
                if target_cycles == 0 or target_cycles < -1:
                    messagebox.showerror("Error",
                                         "Please enter -1 for continuous mode or a positive number for specific cycles")
                    return
                # Collect parameters from GUI
                params = {
                    "target_rpm": float(self.target_rpm.get()),
                    "forward_torque": float(self.forward_torque.get()),
                    "reverse_torque": float(self.reverse_torque.get()),
                    "forward_duration": float(self.forward_duration.get()),
                    "reverse_duration": float(self.reverse_duration.get()),
                    "max_motor_current": float(self.max_motor_current.get()),
                    "max_brake_current": float(self.max_brake_current.get())
                }

                self.running = True
                self.update_status_lights("running")
                self.start_button.config(state="disabled")

                # Start test in separate thread
                self.test_thread = threading.Thread(
                    target=self.run_test_with_monitoring,
                    args=(params, target_cycles)
                )
                self.test_thread.daemon = True
                self.test_thread.start()

            except ValueError as e:
                messagebox.showerror("Error", "Please enter valid numbers for all parameters")
                self.stop_test()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start test: {str(e)}")
                self.stop_test()

    def run_test_with_monitoring(self, params, target_cycles):
        """Runs the test and monitors for completion"""
        try:
            final_cycle = self.motor_controller.start_test(params, target_cycles)
            # If we reach here, test completed successfully
            self.root.after(0, self.handle_test_completion, "completed")
        except Exception as e:
            # If there was an error
            self.root.after(0, self.handle_test_completion, "error")

    def handle_test_completion(self, status):
        """Handles test completion and updates UI accordingly"""
        self.running = False
        self.start_button.config(state="normal")

        if status == "completed":
            self.update_status_lights("completed")
            self.status_message.set("Test Completed Successfully")
            messagebox.showinfo("Success", "Target cycles completed successfully!")
        else:
            self.update_status_lights("stopped")
            self.status_message.set("Test Stopped Due to Error")

    def stop_test(self):
        """Handles the stop button click"""
        self.running = False
        self.update_status_lights("stopped")
        self.start_button.config(state="normal")
        try:
            self.motor_controller.stop_test()
        except Exception as e:
            messagebox.showerror("Error", f"Error stopping test: {str(e)}")

    def update_parameters(self):
        """Updates all GUI parameters with current motor values"""
        if self.running:
            try:
                self.motor_rpm.set(str(self.motor_controller.read_motor_data("motor_rpm")))
                self.motor_temp.set(str(self.motor_controller.read_motor_data("motor_temp")))
                self.controller_temp.set(str(self.motor_controller.read_motor_data("controller_temp")))
                self.battery_voltage.set(f"{self.motor_controller.read_motor_data('battery_voltage'):.1f}")
                self.battery_soc.set(str(self.motor_controller.read_motor_data("battery_state of charge")))

                # Update cycle count
                current_count = self.motor_controller.get_last_cycle_count("No_of_cycles.txt")
                self.current_cycle.set(str(current_count))

                # Check warning conditions
                if float(self.motor_temp.get()) > 80:
                    self.update_status_lights("warning")
                elif float(self.battery_soc.get()) < 30:
                    self.update_status_lights("warning")
                else:
                    self.update_status_lights("running")

            except Exception as e:
                print(f"Error updating parameters: {e}")

        self.root.after(1000, self.update_parameters)

def main():
    root = tk.Tk()
    app = OneWayClutchTesterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()