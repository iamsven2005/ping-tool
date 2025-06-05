from flask import Flask, request, jsonify, abort, render_template
import sqlite3
from flask_cors import CORS  # import CORS
import threading
import time
from ping3 import ping
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from dateutil import parser
import pytz


app = Flask(__name__)
CORS(app)  # enable CORS for all routes
# Configure logging at the start of your app.py
logging.basicConfig(level=logging.DEBUG)  # Default level



BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current script directory
PARENT_DIR = os.path.dirname(BASE_DIR)                 # Parent directory
DB_DIR = os.path.join(PARENT_DIR, 'data')              # 'data' folder in parent dir
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)  # Create /data folder if it doesn't exist

DB_NAME = os.path.join(DB_DIR, 'ips.db')

LOG_DIR = os.path.join(PARENT_DIR, 'log')              # log folder in parent dir
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_path = os.path.join(LOG_DIR, 'ping_server.log')

handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
local_tz = pytz.timezone('Asia/Singapore')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
def ping_all_loop(interval=5):
    while True:
        try:
            conn = get_db_connection()
            ips = conn.execute("SELECT * FROM ips WHERE client = 'host'").fetchall()
            app.logger.debug(f"Pinging {len(ips)} IPs")
            for ip in ips:
                latency = None
                try:
                    latency_sec = ping(ip['ip'], timeout=2)
                    latency = int(latency_sec * 1000) if latency_sec is not None else None
                except Exception as e:
                    app.logger.warning(f"Ping failed for {ip['ip']}: {e}")
                    latency = None

                # ... inside record_ping route ...

                local_now = datetime.now()
                conn.execute('INSERT INTO pings (ip_id, latency_ms, timestamp) VALUES (?, ?, ?)', 
                            (ip['id'], latency, local_now.strftime('%Y-%m-%d %H:%M:%S')))

                conn.commit()
            conn.close()
        except Exception as e:
            app.logger.error(f"Error in ping_all_loop: {e}", exc_info=True)
        time.sleep(interval)


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping-data', methods=['GET'])
def get_ping_data():
    start = request.args.get('start')
    end = request.args.get('end')
    print(start, end)  # Debug log
    def parse_dt(dt_str):
        if not dt_str:
            return None
        try:
            dt_utc = parser.isoparse(dt_str)    # parse with timezone awareness
            dt_local = dt_utc.astimezone(local_tz).replace(tzinfo=None)  # convert to naive local time
            return dt_local
        except Exception as e:
            app.logger.error(f"Failed to parse datetime {dt_str}: {e}")
            return None


    start_dt = parse_dt(start) if start else None
    end_dt = parse_dt(end) if end else None

    conn = get_db_connection()
    ips = conn.execute('SELECT id, ip, name, client FROM ips').fetchall()
    result = []

    for ip in ips:
        query = 'SELECT latency_ms, timestamp FROM pings WHERE ip_id = ?'
        params = [ip['id']]

        if start_dt and end_dt:
            query += ' AND timestamp BETWEEN ? AND ?'
            params.extend([start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")])
        elif start_dt:
            query += ' AND timestamp >= ?'
            params.append(start_dt.strftime("%Y-%m-%d %H:%M:%S"))
        elif end_dt:
            query += ' AND timestamp <= ?'
            params.append(end_dt.strftime("%Y-%m-%d %H:%M:%S"))

        query += ' ORDER BY timestamp ASC'

        app.logger.debug(f"SQL query: {query} with params: {params}")  # Debug log

        pings = conn.execute(query, tuple(params)).fetchall()
        pings_list = [dict(p) for p in pings]

        device_name = ip['name'].strip() or ip['ip']

        result.append({
            "device": device_name,
            "ip": ip['ip'],
            "pings": pings_list,
            "client": ip['client']
        })
    conn.close()
    return jsonify(result)

@app.route('/ips', methods=['GET'])
def get_ips():
    search = request.args.get('search', '').strip().lower()
    conn = get_db_connection()
    if search:
        # Use LIKE with wildcards for partial matching (case-insensitive)
        ips = conn.execute('''
            SELECT * FROM ips 
            WHERE LOWER(name) LIKE ? OR LOWER(ip) LIKE ?
        ''', (f'%{search}%', f'%{search}%')).fetchall()
    else:
        ips = conn.execute('SELECT * FROM ips').fetchall()
    conn.close()
    return jsonify([dict(ip) for ip in ips])


@app.route('/ips/<int:ip_id>', methods=['GET'])
def get_ip(ip_id):
    conn = get_db_connection()
    ip = conn.execute('SELECT * FROM ips WHERE id = ?', (ip_id,)).fetchone()
    conn.close()
    if ip is None:
        abort(404, 'IP not found')
    return jsonify(dict(ip))

@app.route('/ips', methods=['POST'])
def create_ip():
    if not request.json or 'ip' not in request.json:
        app.logger.warning("Create IP failed: no IP provided in request")
        abort(400, 'IP address required')
    ip_addr = request.json['ip']
    name = request.json.get('name', '')
    app.logger.debug(f"Creating IP: {ip_addr} with name: {name}")
    conn = get_db_connection()
    try:
        cur = conn.execute('INSERT INTO ips (ip, name) VALUES (?, ?)', (ip_addr, name))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        
        conn.close()
        abort(400, 'IP address must be unique')
        app.logger.error(f"DB error on create_ip: {e}")
    conn.close()
    return jsonify({'id': new_id, 'ip': ip_addr, 'name': name}), 201


@app.route('/ips/<int:ip_id>', methods=['PUT'])
def update_ip(ip_id):
    if not request.json or 'ip' not in request.json:
        abort(400, 'IP address required')
    ip_addr = request.json['ip']
    name = request.json.get('name', '')
    conn = get_db_connection()
    cur = conn.execute('SELECT * FROM ips WHERE id = ?', (ip_id,))
    if cur.fetchone() is None:
        conn.close()
        abort(404, 'IP not found')
    try:
        conn.execute('UPDATE ips SET ip = ?, name = ? WHERE id = ?', (ip_addr, name, ip_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        abort(400, 'IP address must be unique')
    conn.close()
    return jsonify({'id': ip_id, 'ip': ip_addr, 'name': name})


@app.route('/ips/<int:ip_id>', methods=['DELETE'])
def delete_ip(ip_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT * FROM ips WHERE id = ?', (ip_id,))
    if cur.fetchone() is None:
        conn.close()
        abort(404, 'IP not found')
    conn.execute('DELETE FROM ips WHERE id = ?', (ip_id,))
    conn.commit()
    conn.close()
    return '', 204

if __name__ == '__main__':
    thread = threading.Thread(target=ping_all_loop, args=(60,), daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000)
