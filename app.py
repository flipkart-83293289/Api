import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Logging for Render Console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# FIXED: Standard Flask instantiation with double underscores
app = Flask(name)
CORS(app)

# RAM-only volatile storage
pending_commands = {}
device_results = {}
active_devices = {}

DATA_TTL_SECONDS = 600  # Auto-purge RAM data older than 10 minutes


def cleanup_stale_data():
    current_time = time.time()
    
    expired_results = [
        dev_id for dev_id, data in device_results.items()
        if current_time - data.get("timestamp", 0) > DATA_TTL_SECONDS
    ]
    for dev_id in expired_results:
        device_results.pop(dev_id, None)

    expired_cmds = [
        dev_id for dev_id, data in pending_commands.items()
        if current_time - data.get("timestamp", 0) > DATA_TTL_SECONDS
    ]
    for dev_id in expired_cmds:
        pending_commands.pop(dev_id, None)


@app.route("/", methods=["GET"])
def home():
    cleanup_stale_data()
    return jsonify({
        "status": "online",
        "system": "Device X Automation Relay Server",
        "active_devices_count": len(active_devices),
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200


@app.route("/get-command", methods=["GET"])
def get_command():
    cleanup_stale_data()
    device_id = request.args.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id parameter required"}), 400

    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    if device_id in pending_commands and pending_commands[device_id]:
        command_data = pending_commands.pop(device_id)
        logging.info(f"Delivered command '{command_data['cmd']}' to device: {device_id}")
        return jsonify(command_data), 200

    return jsonify({"cmd": None}), 200


@app.route("/post-result", methods=["POST"])
def post_result():
    cleanup_stale_data()
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")
    result = data.get("result")

    if not device_id or not cmd:
        return jsonify({"error": "Missing device_id or cmd parameters"}), 400

    device_results[device_id] = {
        "cmd": cmd,
        "result": result,
        "timestamp": time.time()
    }

    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Received result for '{cmd}' from device: {device_id}")

    return jsonify({"status": "success"}), 200


@app.route("/send-command", methods=["POST"])
def send_command():
    cleanup_stale_data()
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")

    if not device_id or not cmd:
        return jsonify({"error": "Missing target device_id or cmd parameters"}), 400

    pending_commands[device_id] = {
        "cmd": cmd,
        "timestamp": time.time()
    }

    logging.info(f"Queued command '{cmd}' for target device: {device_id}")

    return jsonify({
        "status": "queued",
        "target_device": device_id,
        "command": cmd
    }), 200


@app.route("/get-result", methods=["GET"])
def get_result():
    cleanup_stale_data()
    device_id = request.args.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id parameter required"}), 400

    if device_id in device_results:
        result_data = device_results.pop(device_id)
        return jsonify(result_data), 200

    return jsonify({"status": "no_data_yet"}), 200


@app.route("/list-devices", methods=["GET"])
def list_devices():
    cleanup_stale_data()
    return jsonify({
        "active_devices": active_devices
    }), 200


if name == "main":
    app.run(host="0.0.0.0", port=5000)
