import pytest
from server.ping_tool_web import app, init_db, get_db_connection

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Clear and re-init DB before each test session
        conn = get_db_connection()
        conn.execute('DROP TABLE IF EXISTS pings')
        conn.execute('DROP TABLE IF EXISTS ips')
        conn.commit()
        conn.close()
        init_db()
        yield client

def test_get_ips_empty(client):
    rv = client.get('/ips')
    assert rv.status_code == 200
    assert rv.json == []

def test_create_and_get_ip(client):
    # Create new IP
    rv = client.post('/ips', json={'ip': '192.168.0.1', 'name': 'Device A'})
    assert rv.status_code == 201
    data = rv.json
    assert data['ip'] == '192.168.0.1'
    assert data['name'] == 'Device A'

    # Get IP list
    rv = client.get('/ips')
    assert rv.status_code == 200
    assert any(ip['ip'] == '192.168.0.1' for ip in rv.json)

def test_update_ip(client):
    rv = client.post('/ips', json={'ip': '10.0.0.1'})
    ip_id = rv.json['id']

    # Update IP and name
    rv = client.put(f'/ips/{ip_id}', json={'ip': '10.0.0.2', 'name': 'New Name'})
    assert rv.status_code == 200
    assert rv.json['ip'] == '10.0.0.2'
    assert rv.json['name'] == 'New Name'

def test_delete_ip(client):
    rv = client.post('/ips', json={'ip': '10.0.0.10'})
    ip_id = rv.json['id']

    rv = client.delete(f'/ips/{ip_id}')
    assert rv.status_code == 204

    rv = client.get(f'/ips/{ip_id}')
    assert rv.status_code == 404

def test_ping_data_endpoint(client):
    rv = client.post('/ips', json={'ip': '8.8.8.8', 'name': 'Google DNS'})
    assert rv.status_code == 201
    assert rv.is_json  # Ensure response is JSON
    ip_id = rv.json['id']  # Should work now

    # Insert ping manually for test
    conn = get_db_connection()
    conn.execute('INSERT INTO pings (ip_id, latency_ms, timestamp) VALUES (?, ?, ?)', (ip_id, 23, '2025-06-01T12:00:00'))
    conn.commit()
    conn.close()

    # Test ping data retrieval
    rv = client.get('/ping-data')
    assert rv.status_code == 200
    found = False
    for device in rv.json:
        if device['ip'] == '8.8.8.8':
            found = True
            assert len(device['pings']) > 0
    assert found
