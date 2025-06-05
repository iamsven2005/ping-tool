import unittest
import json
from recorder_app import app, init_db, get_db_connection

class RecorderAppTestCase(unittest.TestCase):

    def setUp(self):
        # Setup test client and initialize DB fresh for each test
        self.app = app.test_client()
        init_db()
        # Clear DB tables before each test to ensure isolation
        conn = get_db_connection()
        conn.execute('DELETE FROM pings')
        conn.execute('DELETE FROM ips')
        conn.commit()
        conn.close()

    def test_create_ip_success(self):
        payload = {"ip": "10.0.0.1", "client": "testclient"}
        resp = self.app.post('/ips', json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['ip'], "10.0.0.1")
        self.assertEqual(data['client'], "testclient")
        self.assertIn('id', data)

    def test_create_ip_missing_ip(self):
        resp = self.app.post('/ips', json={"client": "testclient"})
        self.assertEqual(resp.status_code, 400)

    def test_create_ip_duplicate(self):
        payload = {"ip": "10.0.0.1", "client": "testclient"}
        resp1 = self.app.post('/ips', json=payload)
        self.assertEqual(resp1.status_code, 201)
        resp2 = self.app.post('/ips', json=payload)
        self.assertEqual(resp2.status_code, 400)

    def test_get_ips_empty(self):
        resp = self.app.get('/ips')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_get_ips_non_empty(self):
        # Insert IP directly
        payload = {"ip": "8.8.8.8", "client": "client1"}
        self.app.post('/ips', json=payload)
        resp = self.app.get('/ips')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(ip['ip'] == "8.8.8.8" and ip['client'] == "client1" for ip in data))

    def test_record_ping_success(self):
        # Create IP first
        payload = {"ip": "1.1.1.1", "client": "client1"}
        self.app.post('/ips', json=payload)

        ping_payload = {"ip": "1.1.1.1", "latency_ms": 123}
        resp = self.app.post('/record-ping/client1', json=ping_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "success")

    def test_record_ping_auto_create_ip(self):
        # Ping an IP that does not exist yet, should auto-create
        ping_payload = {"ip": "9.9.9.9", "latency_ms": 50}
        resp = self.app.post('/record-ping/clientX', json=ping_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "success")

        # Confirm IP created in DB
        resp2 = self.app.get('/ips')
        ips = resp2.get_json()
        self.assertTrue(any(ip['ip'] == "9.9.9.9" and ip['client'] == "clientX" for ip in ips))

    def test_record_ping_missing_fields(self):
        resp = self.app.post('/record-ping/client1', json={"ip": "1.1.1.1"})
        self.assertEqual(resp.status_code, 400)

        resp2 = self.app.post('/record-ping/client1', json={"latency_ms": 10})
        self.assertEqual(resp2.status_code, 400)

    def test_create_ip_defaults_client(self):
        # If client not provided, defaults to 'host'
        payload = {"ip": "10.10.10.10"}
        resp = self.app.post('/ips', json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['client'], 'host')

if __name__ == '__main__':
    unittest.main()
