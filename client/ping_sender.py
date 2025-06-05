import requests
from ping3 import ping
import time
import threading

# Constants for the recorder service
RECORDER_BASE = "http://localhost:5001"
CLIENT_NAME = "client1"

# Refactored ips_to_ping to be list of dicts with name and host
ips_to_ping = [
    {"name": "google dns", "host": "8.8.8.8"},
    {"name": "cloudflare dns", "host": "1.1.1.1"},
    {"name": "local device 1", "host": "192.168.1.26"},
    {"name": "local device 2", "host": "192.168.1.102"},
    {"name": "local device 3", "host": "192.168.1.96"},
]

existing_ips = set()

def fetch_existing_ips():
    global existing_ips
    try:
        resp = requests.get(f"{RECORDER_BASE}/ips")
        resp.raise_for_status()
        existing_ips = set((entry['ip'], entry['client']) for entry in resp.json())
        print(f"Existing IPs from recorder: {existing_ips}")
    except Exception as e:
        print(f"Failed to fetch existing IPs: {e}")

def add_ip(ip):
    try:
        resp = requests.post(f"{RECORDER_BASE}/ips", json={"ip": ip, "client": CLIENT_NAME})
        resp.raise_for_status()
        existing_ips.add((ip, CLIENT_NAME))
        print(f"Added new IP {ip} to recorder")
        return True
    except Exception as e:
        print(f"Failed to add IP {ip}: {e}")
        return False

def send_ping_result(ip_obj, latency_ms):
    payload = {
        "ip": ip_obj["host"],
        "latency_ms": latency_ms,
        "name": ip_obj.get("name", "")  # send device name if available
    }
    try:
        resp = requests.post(f"{RECORDER_BASE}/record-ping/{CLIENT_NAME}", json=payload)
        resp.raise_for_status()
        print(f"Sent ping data for {ip_obj['host']}: {latency_ms} ms")
    except Exception as e:
        print(f"Failed to send ping data for {ip_obj['host']}: {e}")


def ping_and_send(ip_obj):
    ip = ip_obj["host"]
    if (ip, CLIENT_NAME) not in existing_ips:
        added = add_ip(ip)
        if not added:
            print(f"Skipping ping for {ip} because it could not be added.")
            return
    latency = None
    try:
        latency_sec = ping(ip, timeout=2)
        latency = int(latency_sec * 1000) if latency_sec is not None else None
    except Exception as e:
        print(f"Ping failed for {ip}: {e}")
    send_ping_result(ip_obj, latency)

def ping_loop(interval=10):
    fetch_existing_ips()
    while True:
        threads = []
        for ip_obj in ips_to_ping:
            t = threading.Thread(target=ping_and_send, args=(ip_obj,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        time.sleep(interval)

if __name__ == "__main__":
    ping_loop()
