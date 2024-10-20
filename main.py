import signal
import sys
import time
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from asgiref.wsgi import WsgiToAsgi
import subprocess
import os
from threading import Thread, Lock
import uvicorn
from config.settings import settings
from config.logger import LOG_LEVEL, UVICORN_LOGGING_CONFIG, setup_logging
from loguru import logger

#
# CONFIG
#

ssl_activated = settings.SV_SSL_CERTFILE and settings.SV_SSL_KEYFILE
setup_logging(LOG_LEVEL, False)

# Start script required for migrations!
if not settings.STARTSCRIPT:
    logger.error(f"Please run this application with start script!")
    sys.exit(3)
    
#
# FLOW
#

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # for flash messaging

task_running = False
process = None
output_buffer = []  # To store the output
buffer_lock = Lock()  # A lock to handle access to the output buffer

# Status
@app.route("/status")
def status():
    global output_buffer, task_running
    msg = "Ready for new action."
    if task_running:
        global process
        print(process.pid,flush=True)
        msg = f"Task is currently running (PID: {process.pid})."
    with buffer_lock:
        return jsonify({
            "msg": msg,
            "task_running": task_running,
            "output": "\n".join(output_buffer)
        })
   
# Start
@app.route("/start", methods=["POST"])
def start():
    global task_running
    mnemonic = request.form.get("mnemonic")
    if mnemonic:
        if task_running:
            msg = "Task is already running. Please wait until it finishes or abort."
        else:
            # Start the background task
            msg = "Starting the signing process..."
            thread = Thread(target=run_task, args=(mnemonic,))
            thread.start()
            task_running = True
    else:
        msg = "Please enter the mnemonic."
    return jsonify({
        "msg": msg,
        "task_running": task_running
    })

# Home page with mnemonic input and buttons
@app.route("/", methods=["GET"])
def home():
    global task_running
    return render_template("index.html", task_running=task_running)

# Route for aborting the process
@app.route("/abort")
def abort_task():
    global process, task_running
    output_buffer.clear()  # Clear previous buffer
    if task_running:
        if process:
            # os.kill(process.pid, signal.SIGTERM)
            # #process.terminate()
            # time.sleep(1)
            # if process.poll() is None:
            #     print("Process did not terminate, force killing...", flush=True)
            #     #process.kill()
            #     os.kill(process.pid, signal.SIGKILL)
            # if process.poll() is not None:
            #     msg = "Signing process aborted successfully."
            #     task_running = False
            # else:
            #     msg = "Failed to terminate process."
            # #msg = "Signing process aborted."
            process.kill()
            subprocess.run(["pkill", "-9","-f", "ethdo"])
            subprocess.run(["pkill", "-9", "-f", "exitsigner"])
            msg = "Signing process aborted."
        else:
            msg = "No process found to abort."
        task_running = False
    else:
        msg = "No task is currently running."
    return jsonify({
        "msg": msg,
        "task_running": task_running
    })

def run_task(mnemonic):
    global process, task_running
    #task_running = True
    output_buffer.clear()  # Clear previous buffer
    # Existigner CLI can be a long-running task with the mnemonic
    try:
        # Run exitsigner
        print("START!!!!!", flush=True)
        # Start the process and capture stdout and stderr
        process = subprocess.Popen(
            #["python", "exitsigner.py", "--mnemonic", mnemonic],
            #f"dist/exitsigner --testing 20",
            f"dist/exitsigner --mnemonic '{mnemonic}'",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # Line buffering
            text=True,
            shell=True,
        )
        # Read the output asynchronously and store it in the buffer
        for stdout_line in iter(process.stdout.readline, ""):
            with buffer_lock:
                output_buffer.append(stdout_line.strip())
                print(f"OUTPUT: {stdout_line.strip()}", flush=True)  # Optionally log to console
        # Handle stderr if needed
        for stderr_line in iter(process.stderr.readline, ""):
            with buffer_lock:
                output_buffer.append(f"ERROR: {stderr_line.strip()}")
                print(f"ERROR: {stderr_line.strip()}", flush=True)
        process.stdout.close()
        process.stderr.close()
        process.wait()  # Wait for the process to complete
        print("COMPLETE!!!!!", flush=True)
        task_running = False

    except Exception as e:
        print(f"Error running process: {e}")
    finally:
        task_running = False

# Convert WSGI Flask app to ASGI (to make it uvicorn compatible)      
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":

    lifespanx = "auto" # auto | on
    reload = False if settings.DOCKERIZED or not settings.AUTORELOAD else True
    uvicorn.run(
        "main:asgi_app",
        host=settings.SV_ADDR,
        port=settings.SV_PORT,
        reload=reload,
        log_config=UVICORN_LOGGING_CONFIG,
        lifespan=lifespanx,
        ssl_certfile=settings.SV_SSL_CERTFILE if ssl_activated else "",
        ssl_keyfile=settings.SV_SSL_KEYFILE if ssl_activated else "",
        ssl_keyfile_password=settings.SV_SSL_KEYFILE_PASS if ssl_activated else "",
        workers=settings.SV_WORKERS 
    )