# Ping Tool Flask Application Documentation

## Overview

This Flask-based API application provides a simple service to manage IP addresses and perform periodic ping tests to measure latency. It stores IPs and their ping results in an SQLite database, and supports CRUD operations on IPs and retrieval of ping data over specified time ranges. It also logs activity and errors with rotating log files.

---

## Features

* **CRUD API for IP addresses** (`/ips` endpoint)
* **Retrieve ping latency data** for stored IPs (`/ping-data` endpoint)
* **Background thread** for continuous periodic pinging of all registered IPs
* **CORS enabled** for cross-origin API access
* **Rotating file logging** for error and info logging
* **SQLite database storage** with two tables: `ips` and `pings`

---

## Project Structure

* `app.py` (this file): main Flask application with API routes, background ping thread, and database initialization.
* `data/ips.db`: SQLite database file storing IPs and ping results (created if not present).
* `logs/ping_tool.log`: Rotating log file for application logs.

---

## Dependencies

* `Flask` — Web framework
* `flask_cors` — To enable CORS
* `ping3` — To perform ping operations
* `sqlite3` — Built-in Python SQLite database
* `logging` — Standard logging with rotating file handler
* `threading` — For running background ping loop

---

## Environment Setup

Make sure to install dependencies via pip:

```bash
pip install Flask flask-cors ping3
```

---

## Configuration Constants

* **Database file location:** `../data/ips.db` relative to the script location.
* **Logging directory:** `logs/`
* **Log file:** `logs/ping_tool.log` with max size 10MB, keeping 5 backups.

---

## Database Schema

### Table: `ips`

| Column | Type    | Description                    |
| ------ | ------- | ------------------------------ |
| id     | INTEGER | Primary key, auto-incremented  |
| ip     | TEXT    | IP address (unique, not null)  |
| client | TEXT    | Client type, default 'host'    |
| name   | TEXT    | Optional device or client name |

### Table: `pings`

| Column      | Type     | Description                                                  |
| ----------- | -------- | ------------------------------------------------------------ |
| id          | INTEGER  | Primary key, auto-incremented                                |
| ip\_id      | INTEGER  | Foreign key referencing `ips.id`                             |
| latency\_ms | INTEGER  | Ping latency in milliseconds (nullable)                      |
| timestamp   | DATETIME | Timestamp when ping was recorded (default current timestamp) |

---

## API Endpoints

### 1. `GET /ping-data`

Retrieve ping latency data for all IPs, optionally filtered by a time range.

* Query Parameters:

  * `start` (optional): ISO 8601 datetime string to filter pings from this time.
  * `end` (optional): ISO 8601 datetime string to filter pings up to this time.

* Response: JSON array of objects, each containing:

  * `device`: device name or IP if no name
  * `ip`: IP address string
  * `pings`: list of ping records `{latency_ms, timestamp}`
  * `client`: client string from `ips` table

---

### 2. `GET /ips`

Retrieve all stored IPs or filtered by a search term.

* Query Parameters:

  * `search` (optional): Partial case-insensitive search string matching IP or name

* Response: JSON array of IP records.

---

### 3. `GET /ips/<int:ip_id>`

Retrieve a single IP record by its ID.

* Response: JSON object with IP details.

* Errors:

  * `404` if IP not found.

---

### 4. `POST /ips`

Create a new IP record.

* Request Body (JSON):

  * `ip`: IP address string (required)
  * `name`: optional device name string

* Response:

  * `201 Created` with created IP record including assigned `id`.

* Errors:

  * `400` if `ip` not provided.
  * `400` if IP address violates uniqueness constraint.

---

### 5. `PUT /ips/<int:ip_id>`

Update an existing IP record by ID.

* Request Body (JSON):

  * `ip`: new IP address string (required)
  * `name`: optional new device name string

* Response: Updated IP record JSON.

* Errors:

  * `400` if `ip` not provided.
  * `404` if IP not found.
  * `400` if IP address violates uniqueness.

---

### 6. `DELETE /ips/<int:ip_id>`

Delete an IP record by ID.

* Response: Empty response with status `204 No Content`.

* Errors:

  * `404` if IP not found.

---

## Background Process

* A background daemon thread runs continuously every 60 seconds by default.
* It fetches all IPs with `client='host'` from the database.
* Pings each IP using the `ping3` library with a 2-second timeout.
* Logs ping failures and stores ping results (latency in ms or `null` if failed) in the `pings` table.

---

## Logging

* Logs stored in `logs/ping_tool.log`.
* Rotates when file size reaches 10MB, keeping 5 backups.
* Logs info and errors related to ping attempts, database operations, and API calls.
* Flask default logs supplemented by a rotating file handler.

---

## How to Run

```bash
python app.py
```

* Runs Flask server on `0.0.0.0:5000`.
* Starts ping background thread automatically.

---

## Notes and Recommendations

* The database connection is opened and closed per request and per background task iteration.
* Consider adding input validation for IP format and unique constraints at the app level if needed.
* The ping loop interval can be adjusted by changing the argument in the background thread creation line (`args=(60,)`).
* Ensure proper firewall and permissions to allow ping operations on your hosting environment.