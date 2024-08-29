from fastapi.testclient import TestClient

from context import isprinklr

from isprinklr.main import app

client = TestClient(app)

def test_get_status():
  response = client.get("/api/status")
  assert response.status_code == 200
  assert response.json() == {"systemStatus": "inactive", "message": "System inactive", "duration": 0}

def test_get_sprinklers():
    response = client.get("/api/sprinklers")
    assert response.status_code == 200
    sprinklers = response.json()
    assert isinstance(sprinklers, list)
    assert len(sprinklers) > 0
    assert all(isinstance(item, dict) for item in sprinklers)
    assert all("zone" in item and "name" in item for item in sprinklers)

def test_get_schedule():
    response = client.get("/api/get_schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert isinstance(schedule, list)
    assert len(schedule) > 0
    assert all(isinstance(item, dict) for item in schedule)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule)
  
def test_get_schedule_on_off():
    response = client.get("/api/get_schedule_on_off")
    assert response.status_code == 200
    schedule_on_off = response.json()
    assert isinstance(schedule_on_off, dict)

def test_get_api_log():
    response = client.get("/api/api_log")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
  
def test_get_scheduler_log():
    response = client.get("/api/scheduler_log")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0

def test_get_serial_log():
    response = client.get("/api/serial_log")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) > 0