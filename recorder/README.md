# Ping Recorder Flask Application Documentation

## Overview

This Flask API service manages IP addresses with associated client identifiers and records ping latency data for those IPs. It supports adding IPs, listing stored IPs, and recording ping latency for specific IP-client combinations.

---

## Features

* **Add new IP with client identifier** (`POST /ips`)
* **List all stored IPs with their clients** (`GET /ips`)
* **Record ping latency for an IP under a specific client** (`POST /record-ping/<client>`)
* **Uses SQLite database with two tables:** `ips` and `pings`
* **Automatic creation of database and tables on startup**

---

## Database Schema

### Table: `ips`

| Column | Type    | Description                           |
| ------ | ------- | ------------------------------------- |
| id     | INTEGER | Primary key, auto-incremented         |
| ip     | TEXT    | IP address (required)                 |
| client | TEXT    | Client identifier, defaults to 'host' |
| name   | TEXT    | *Not used in this version*            |

### Table: `pings`

| Column      | Type     | Description                           |
| ----------- | -------- | ------------------------------------- |
| id          | INTEGER  | Primary key, auto-incremented         |
| ip\_id      | INTEGER  | Foreign key referencing `ips.id`      |
| latency\_ms | INTEGER  | Latency in milliseconds               |
| timestamp   | DATETIME | Timestamp of ping record, default now |

---

## Environment Setup

* Requires Python 3.x and `Flask`.
* Install dependencies:

  ```bash
  pip install Flask
  ```
* The SQLite database file is created under `../data/ips.db` relative to this script.

---

## API Endpoints

### 1. `POST /ips`

Add a new IP with an optional client identifier.

* Request JSON:

  ```json
  {
    "ip": "192.168.1.1",
    "client": "host"  // Optional, defaults to "host"
  }
  ```

* Responses:

  * `201 Created` with JSON of new record:

    ```json
    {
      "id": 1,
      "ip": "192.168.1.1",
      "client": "host"
    }
    ```
  * `400 Bad Request` if IP is missing or IP+client already exists.

---

### 2. `GET /ips`

Retrieve a list of all stored IPs with their client identifiers.

* Response JSON:

  ```json
  [
    {"ip": "192.168.1.1", "client": "host"},
    {"ip": "10.0.0.1", "client": "deviceA"}
  ]
  ```

---

### 3. `POST /record-ping/<string:client>`

Record a ping latency measurement for a given IP and client.

* URL parameter:

  * `client` — the client identifier (e.g., `host`, `deviceA`)

* Request JSON:

  ```json
  {
    "ip": "192.168.1.1",
    "latency_ms": 25
  }
  ```

* Behavior:

  * If the IP+client combination does not exist, it is automatically inserted into `ips`.
  * A new ping record with `latency_ms` is inserted with a timestamp.

* Responses:

  * `200 OK` with JSON:

    ```json
    {"status": "success"}
    ```
  * `400 Bad Request` if `ip` or `latency_ms` is missing in request.

---

## How to Run

```bash
python app.py
```

* The app listens on `0.0.0.0:5001`.
* Initializes database and tables if not present.

---

## Notes

* The database file is stored relative to the script, two directories up in `data/ips.db`.
* The app does not currently expose endpoints for retrieving ping data or deleting IPs.
* `name` field in `ips` table exists in DB schema but is unused in this version.
* No authentication or rate limiting is implemented.
* Ensure the client sending pings uses the correct `<client>` path parameter to match or create IP entries.