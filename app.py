from flask import Flask, request, jsonify
import time

app = Flask(name)

# In-Memory Stores (RAM Only - No Database)
pending_commands = {}
device_results = {}
active_devices = {}


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "system": "Device X Automation Relay Server",
        "active_devices_count": len(active_devices)
    }), 200


# ==========================================
# 1. ANDROID APP ENDPOINTS (Device X)
# ==========================================

@app.route("/get-command", methods=["GET"])
def get_command():
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    if device_id in pending_commands and pending_commands[device_id]:
        command_data = pending_commands.pop(device_id)
        return jsonify(command_data), 200

    return jsonify({"cmd": None}), 200


@app.route("/post-result", methods=["POST"])
def post_result():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")
    result = data.get("result")

    if not device_id or not cmd:
        return jsonify({"error": "Missing device_id or cmd"}), 400

    device_results[device_id] = {
        "cmd": cmd,
        "result": result,
        "timestamp": time.time()
    }

    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({"status": "success"}), 200


# ==========================================
# 2. DASHBOARD / CONTROLLER ENDPOINTS (Device Y)
# ==========================================

@app.route("/send-command", methods=["POST"])
def send_command():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")

    if not device_id or not cmd:
        return jsonify({"error": "Missing target device_id or cmd"}), 400

    pending_commands[device_id] = {
        "cmd": cmd,
        "timestamp": time.time()
    }

    return jsonify({
        "status": "queued",
        "target_device": device_id,
        "command": cmd
    }), 200


@app.route("/get-result", methods=["GET"])
def get_result():
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id parameter required"}), 400

    if device_id in device_results:
        result_data = device_results.pop(device_id)
        return jsonify(result_data), 200

    return jsonify({"status": "no_data_yet"}), 200


@app.route("/list-devices", methods=["GET"])
def list_devices():
    return jsonify({
        "active_devices": active_devices
    }), 200


if name == "main":
    app.run(host="0.0.0.0", port=5000)
