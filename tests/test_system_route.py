from fastapi.testclient import TestClient
import pytest
from unittest import mock

from context import isprinklr
from isprinklr.main import app
from isprinklr.system_status import system_status
import isprinklr.esp_controller as esp_controller

client = TestClient(app)

# Use this to set up for all tests
@pytest.fixture(autouse=True)
def mock_esp_controller():
    # Create a dummy status response
    dummy_status = {
        "status": "ok",
        "uptime_ms": 82077541,
        "chip": {
            "model": "ESP32-S3",
            "revision": 2,
            "cores": 2
        },
        "memory": {
            "free_heap": 8651544,
            "min_free_heap": 8648992
        },
        "network": {
            "connected": True,
            "type": "Ethernet",
            "ip": "192.168.88.24"
        }
    }
    
    # Mock the test_awake function to return the dummy status instead of connecting to hardware
    with mock.patch('isprinklr.esp_controller.test_awake', return_value=dummy_status):
        # Yield control back to the test
        yield

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
  
  # Get the response data
  response_data = response.json()
  
  # Basic status fields should always be present
  assert "systemStatus" in response_data
  assert "message" in response_data 
  assert "active_zone" in response_data
  assert "duration" in response_data
  
  # The basic status values should match these defaults
  assert response_data["systemStatus"] == "inactive"
  assert response_data["message"] is None
  assert response_data["active_zone"] is None
  assert response_data["duration"] == 0
  
  # ESP status should be included since we're mocking the connection
  assert "esp_status" in response_data
  assert isinstance(response_data["esp_status"], dict)
  assert "status" in response_data["esp_status"]
  assert response_data["esp_status"]["status"] == "ok"
  
  # Verify some deeper nested fields are present
  assert "chip" in response_data["esp_status"]
  assert "model" in response_data["esp_status"]["chip"]
  assert response_data["esp_status"]["chip"]["model"] == "ESP32-S3"
  
  assert "network" in response_data["esp_status"]
  assert "connected" in response_data["esp_status"]["network"]
  assert response_data["esp_status"]["network"]["connected"] == True
