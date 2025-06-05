# Ping Client Script Documentation

## Overview

This Python script continuously pings a list of IP addresses, records their latency, and sends the results to a separate ping recorder Flask API server. It manages IP registration with the recorder before sending ping data and operates in a loop with a configurable interval.

---

## Features

* Pings multiple IP addresses periodically.
* Automatically registers new IPs with the recorder API if they do not exist.
* Sends ping latency data to the recorder API for storage.
* Handles errors gracefully and prints relevant status messages.
* Uses `ping3` for ICMP pinging.
* Uses `requests` to interact with the recorder API.

---

## Dependencies

* `requests` — For HTTP requests.
* `ping3` — For sending ICMP ping requests.
* `time` — For loop interval control.

Install dependencies with:

```bash
pip install requests ping3
```

---

## Configuration

* `RECORDER_BASE` — Base URL of the ping recorder API (default: `http://localhost:5001`).
* `ips_to_ping` — List of IP addresses to be pinged continuously.
* `interval` — Ping loop delay in seconds (default 10).

---

## Functions

### `fetch_existing_ips()`

* Fetches the list of IPs currently registered on the recorder API.
* Updates the global `existing_ips` set with the fetched IPs.
* Prints status or error messages.

---

### `add_ip(ip)`

* Registers a new IP with the recorder API by sending a POST request to `/ips`.
* Updates `existing_ips` on success.
* Returns `True` if successful, `False` otherwise.
* Prints success or error messages.

---

### `send_ping_result(ip, latency_ms)`

* Sends ping latency data to the recorder API endpoint `/record-ping/client1`.
* Payload JSON format:

  ```json
  {
    "ip": "<ip_address>",
    "latency_ms": <latency_in_milliseconds or null>
  }
  ```
* Prints confirmation or error messages.

---

### `ping_loop(interval=10)`

* Main loop function that:

  * Calls `fetch_existing_ips()` once at start.
  * For each IP in `ips_to_ping`:

    * Checks if IP is registered; if not, attempts to register it.
    * Pings the IP with a 2-second timeout using `ping3`.
    * Converts latency from seconds to milliseconds (or sets to `None` if ping fails).
    * Sends ping result to the recorder.
  * Waits for `interval` seconds before repeating.

---

## How to Run

Run the script directly:

```bash
python ping_client.py
```

Make sure the recorder API server is running and accessible at the URL specified in `RECORDER_BASE`.

---

## Notes

* The script assumes the recorder API uses a client ID `client1` when sending ping data. Modify this as needed.
* Ping failures result in latency being sent as `null` (or `None` in Python).
* IP registration is done per IP only once at startup or when encountering a new IP.
* The script prints detailed logs to the console for monitoring progress and errors.
* You can modify `ips_to_ping` to add or remove IPs to be monitored.