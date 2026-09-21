import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cross-Origin Requests को अलाउ करने के लिए

# Secret Key और Admin Credentials (अपने हिसाब से बदलें)
app.config['SECRET_KEY'] = 'SUPER_SECRET_STRONG_KEY_12345'
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

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

# --- 1. Root Route (कोई भी डायरेक्ट लिंक खोले तो 404/Error दिखेगा) ---
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "error",
        "message": "Access Denied. Resource Not Found."
    }), 404

# --- 2. Login Endpoint ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"status": "error", "message": "Username and Password required"}), 400
    
    if data['username'] == ADMIN_USERNAME and data['password'] == ADMIN_PASSWORD:
        # Token valid for 24 hours
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

# --- 3. Command Execution Endpoint (JSON in -> JSON out) ---
@app.route('/api/execute', methods=['POST'])
@token_required
def execute_command():
    data = request.get_json()
    
    if not data or 'command' not in data:
        return jsonify({"status": "error", "message": "No command provided"}), 400
    
    command = data.get('command')
    payload = data.get('payload', {})
    
    # यहाँ आप अपनी कस्टम कमांड लॉजिक जोड़ सकते हैं
    if command == "get_system_info":
        result = {
            "server_status": "Active",
            "region": "Render-Cloud",
            "python_version": "3.10+",
            "active_tasks": 5
        }
    elif command == "process_data":
        result = {
            "processed": True,
            "received_payload": payload,
            "records_updated": 12
        }
    else:
        result = {
            "info": f"Executed custom command: {command}",
            "custom_data": payload
        }

    return jsonify({
        "status": "success",
        "command_executed": command,
        "result": result,
        "timestamp": str(datetime.datetime.now())
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
