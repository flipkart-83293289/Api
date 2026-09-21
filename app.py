import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # क्रॉस-ओरिजिन रिक्वेस्ट की अनुमति देने के लिए

# सीक्रेट की और एडमिन क्रेडेंशियल्स
app.config['SECRET_KEY'] = 'SUPER_SECRET_STRONG_KEY_12345'
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# इन-मेमोरी स्टोरेज (डेटा सेव करने के लिए)
pending_commands = {}
device_telemetry_results = {}
last_sent_commands = {}  # यह ट्रैक करेगा कि ऐप को कौन सी कमांड भेजी गई थी

# --- ऑथेंटिकेशन डेकोरेटर (डैशबोर्ड के लिए) ---
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

# --- रूट राउट ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "error",
        "message": "Render API Hub is running successfully."
    }), 200

# --- लॉगिन एंडपॉइंट (डैशबोर्ड ऑथेंटिकेशन) ---
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

# --- कमांड एक्जीक्यूट एंडपॉइंट (डैशबोर्ड से कमांड कतार में डालने के लिए) ---
@app.route('/api/execute', methods=['POST'])
@token_required
def execute_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    
    command = data.get('command')
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    # कमांड को पेंडिंग queue में डालना
    pending_commands[device_id] = command

    return jsonify({
        "status": "success",
        "command_executed": command,
        "target_device": device_id,
        "message": "Command queued successfully.",
        "timestamp": str(datetime.datetime.now())
    }), 200

# --- एंड्रॉइड ऐप कमांड फेच एंडपॉइंट ---
@app.route('/api/v1/command/fetch', methods=['GET'])
def fetch_command():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    cmd = pending_commands.get(device_id, "none")
    
    if cmd != "none":
        # कमांड को याद रखना ताकि ऐप का रिजल्ट आने पर मैच किया जा सके
        last_sent_commands[device_id] = cmd
        pending_commands[device_id] = "none"

    return jsonify({
        "cmd": cmd,
        "status": "success"
    }), 200

# --- एंड्रॉइड ऐप टेलीमेट्री / रिजल्ट पोस्ट एंडपॉइंट ---
@app.route('/api/v1/telemetry', methods=['POST'])
def post_telemetry():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
        
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    # यदि ऐप 'cmd' भेजना भूल गया है, तो सर्वर अपनी मेमोरी से आखिरी भेजी गई कमांड उठा लेगा
    cmd = data.get('cmd') or last_sent_commands.get(device_id, 'Unknown Command')
    result_data = data.get('result', data)
    
    # डैशबोर्ड के लिए रिजल्ट सेव करना
    device_telemetry_results[device_id] = {
        "command": cmd,
        "result": result_data,
        "timestamp": str(datetime.datetime.now())
    }

    return jsonify({
        "status": "success",
        "message": "Telemetry received successfully"
    }), 200

# --- डैशबोर्ड के लिए लेटेस्ट रिजल्ट प्राप्त करने का एंडपॉइंट ---
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
