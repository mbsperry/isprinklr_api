from fastapi.testclient import TestClient

from context import isprinklr
from isprinklr.main import app
from isprinklr.system_status import system_status

client = TestClient(app)

def test_get_last_sprinkler_run_none():
    response = client.get("/api/system/last-sprinkler-run")
    assert response.status_code == 200
    assert response.json() is None

def test_get_last_sprinkler_run():
    # Set test data
    system_status.last_zone_run = 3
    
    response = client.get("/api/system/last-sprinkler-run")
    data = response.json()
    
    assert response.status_code == 200
    assert isinstance(data, dict)
    assert "zone" in data
    assert "timestamp" in data
    assert data["zone"] == 3
    
    # Reset test data
    system_status._last_zone_run = None

def test_get_last_schedule_run_none():
    # Reset test data
    system_status._last_schedule_run = None
    
    response = client.get("/api/system/last-schedule-run")
    assert response.status_code == 200
    assert response.json() is None

def test_get_last_schedule_run():
    # Set test data
    system_status.last_schedule_run = {
        "name": "Daily Schedule",
        "message": "success"
    }
    
    response = client.get("/api/system/last-schedule-run")
    data = response.json()
    
    assert response.status_code == 200
    assert isinstance(data, dict)
    assert "name" in data
    assert "timestamp" in data
    assert "message" in data
    assert data["name"] == "Daily Schedule"
    assert data["message"] == "success"
    
    # Reset test data
    system_status._last_schedule_run = None

def test_get_status():
  response = client.get("/api/system/status")
  assert response.status_code == 200
  assert response.json() == {"systemStatus": "inactive", "message": None, "active_zone": None, "duration": 0}
