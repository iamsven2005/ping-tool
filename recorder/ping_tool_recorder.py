from flask import Flask, request, jsonify, abort
import sqlite3
import os
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# ... your existing imports and code ...

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current script directory
PARENT_DIR = os.path.dirname(BASE_DIR)                 # Parent directory
DB_DIR = os.path.join(PARENT_DIR, 'data')              # 'data' folder in parent dir
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)  # Create /data folder if it doesn't exist

DB_NAME = os.path.join(DB_DIR, 'ips.db')

LOG_DIR = os.path.join(PARENT_DIR, 'log')              # log folder in parent dir
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'ping_tool.log')

# Setup logging
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to Flask's app logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

# Now you can use app.logger.debug(), app.logger.error() etc. in your routes and functions

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    app.logger.debug("Initializing database...")
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            client TEXT DEFAULT 'host',
            name TEXT DEFAULT ''
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_id INTEGER NOT NULL,
            latency_ms INTEGER,
            timestamp DATETIME,  -- no default
            FOREIGN KEY (ip_id) REFERENCES ips (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
    app.logger.debug("Database initialized.")

@app.route('/ips', methods=['POST'])
def create_ip():
    data = request.json
    ip = data.get('ip')
    client = data.get('client', 'host')
    if not ip:
        app.logger.warning("Create IP failed: no IP provided")
        abort(400, "IP address is required")
    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM ips WHERE ip = ? AND client = ?', (ip, client)).fetchone()
    if existing:
        app.logger.debug(f"IP {ip} with client {client} already exists. Returning existing entry.")
        conn.close()
        return jsonify({'id': existing['id'], 'ip': ip, 'client': client}), 200

    cur = conn.execute('INSERT INTO ips (ip, client) VALUES (?, ?)', (ip, client))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    app.logger.debug(f"Created IP {ip} for client {client} with id {new_id}")
    return jsonify({'id': new_id, 'ip': ip, 'client': client}), 201

@app.route('/ips', methods=['GET'])
def get_ips():
    conn = get_db_connection()
    ips = conn.execute('SELECT ip, client FROM ips').fetchall()
    conn.close()
    app.logger.debug(f"Fetched {len(ips)} IPs")
    return jsonify([{'ip': ip['ip'], 'client': ip['client']} for ip in ips])

@app.route('/record-ping/<string:client>', methods=['POST'])
def record_ping(client):
    data = request.json
    ip = data.get('ip')
    latency = data.get('latency_ms')
    name = data.get('name', '')  # get device name, default empty string

    if not ip or latency is None:
        app.logger.warning("Record ping failed: missing 'ip' or 'latency_ms'")
        abort(400, "Missing 'ip' or 'latency_ms' in JSON payload")

    conn = get_db_connection()
    ip_row = conn.execute('SELECT id, name FROM ips WHERE ip = ? AND client = ?', (ip, client)).fetchone()

    if ip_row is None:
        # Insert new IP with name
        cur = conn.execute('INSERT INTO ips (ip, client, name) VALUES (?, ?, ?)', (ip, client, name))
        conn.commit()
        ip_id = cur.lastrowid
        app.logger.debug(f"Auto-created IP {ip} for client {client} with id {ip_id} and name '{name}'")
    else:
        ip_id = ip_row['id']
        # If name is non-empty and different from current, update it
        if name and name != ip_row['name']:
            conn.execute('UPDATE ips SET name = ? WHERE id = ?', (name, ip_id))
            conn.commit()
            app.logger.debug(f"Updated name for IP {ip} client {client} to '{name}'")

    # Insert ping record
    local_now = datetime.now()
    conn.execute('INSERT INTO pings (ip_id, latency_ms, timestamp) VALUES (?, ?, ?)', 
                (ip_id, latency, local_now.strftime('%Y-%m-%d %H:%M:%S')))    
    conn.commit()
    conn.close()
    app.logger.debug(f"Recorded ping for IP {ip} client {client} latency {latency} ms with name '{name}'")
    return jsonify({"status": "success"})


if __name__ == '__main__':
    init_db()
    app.logger.debug("Starting Flask app...")
    app.run(host='0.0.0.0', port=5001)
