from flask import Flask
import subprocess
import os
import platform

app = Flask(__name__)

# Root Route (Fixes 404 Error)
@app.route('/', methods=['GET'])
def home():
    return "Flask API is running! Use /start_gui to launch the GUI."

@app.route('/Start_OWC', methods=['GET'])
def start_gui():
    try:
        system_os = platform.system()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        gui_script = os.path.join(base_dir, "gui.py")

        if system_os == "Windows":
            venv_path = os.path.join(base_dir, "venv", "Scripts", "activate.bat")
            command = f'start cmd /k "{venv_path} && python {gui_script}"'
        else:
            venv_path = os.path.join(base_dir, "venv", "bin", "activate")
            command = f'/bin/bash -c "source {venv_path} && python {gui_script}"'

        subprocess.Popen(command, shell=True)
        return "GUI started successfully!", 200

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
