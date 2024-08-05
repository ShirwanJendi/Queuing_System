from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import pymysql
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database configuration
DB_HOST = 'localhost'
DB_USER = 'shero'
DB_PASSWORD = '1234'
DB_NAME = 'mobilsyn_newdb'
DB_TABLE = 'tracking_info'

# MQTT configuration
MQTT_SERVER = 'localhost'
MQTT_TOPIC = 'esp32/button'

# Initialize MQTT client
mqtt_client = mqtt.Client()

# Store numbers and their timestamps
tracking_numbers = {}

def db_connect():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def save_to_db(number, device_name, repair_info, repair_time, created_at, time_remain):
    conn = db_connect()
    try:
        with conn.cursor() as cursor:
            sql = f"INSERT INTO {DB_TABLE} (number, device_name, repair_info, repair_time, created_at, time_remain) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (number, device_name, repair_info, repair_time, created_at, time_remain))
        conn.commit()
    finally:
        conn.close()

@app.route('/')
def index():
    return render_template('technician.html')

@socketio.on('connect')
def test_connect():
    emit('my_response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@app.route('/update_number', methods=['POST'])
def update_number():
    data = request.json
    number = data.get('number', '')
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tracking_numbers[number] = created_at
    socketio.emit('number_update', {'number': number, 'timestamp': created_at})
    return jsonify({"number": number})

@app.route('/save_info', methods=['POST'])
def save_info():
    data = request.json
    number = data.get('number')
    device_name = data.get('device_name')
    repair_info = data.get('repair_info')
    repair_time = data.get('repair_time')
    created_at = data.get('created_at')
    time_remain = (datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S') + timedelta(minutes=int(repair_time))).strftime('%Y-%m-%d %H:%M:%S')
    
    save_to_db(number, device_name, repair_info, repair_time, created_at, time_remain)
    return jsonify({"status": "success"})

@app.route('/get_latest_numbers')
def get_latest_numbers():
    cutoff_time = datetime.now() - timedelta(minutes=30)
    recent_numbers = [
        {"number": number, "timestamp": timestamp}
        for number, timestamp in tracking_numbers.items()
        if datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') > cutoff_time
    ]
    return jsonify(recent_numbers)

def on_mqtt_message(client, userdata, msg):
    number = msg.payload.decode()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tracking_numbers[number] = created_at
    socketio.emit('number_update', {'number': number, 'timestamp': created_at})
    print(f"Received MQTT message: {number}")

mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_SERVER)
mqtt_client.subscribe(MQTT_TOPIC)
mqtt_client.loop_start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)