from fastapi.testclient import TestClient

from context import isprinklr
import isprinklr.paths
import isprinklr.system


from isprinklr.main import app

client = TestClient(app)

def test_get_schedule(mocker):
    mocker.patch('isprinklr.system.system_status.get_schedule', return_value=[{"zone": "zone1", "day": "M", "duration": 1800}])  # 30 minutes in seconds
    response = client.get("/api/scheduler/schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert isinstance(schedule, list)
    assert len(schedule) == 1
    assert all(isinstance(item, dict) for item in schedule)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule)

def test_get_schedule_on_off(mocker):
    isprinklr.system.system_status.schedule_on_off = True
    # mocker.patch('isprinklr.system.system_status.schedule_on_off', return_value=True)
    response = client.get("/api/scheduler/on_off")
    assert response.status_code == 200
    schedule_on_off = response.json()
    assert isinstance(schedule_on_off, dict)
    assert isinstance(schedule_on_off["schedule_on_off"], bool)
    assert schedule_on_off["schedule_on_off"] == True

def test_update_schedule_on_off(mocker):
    # mocker.patch('isprinklr.system.SystemStatus.schedule_on_off', new_callable=mocker.PropertyMock, return_value=False)
    response = client.put("/api/scheduler/on_off", params={"schedule_on_off": False})
    assert response.status_code == 200
    assert response.json() == {"schedule_on_off": False}

def test_update_schedule(mocker):
    mocker.patch('isprinklr.system.system_status.update_schedule', return_value=True)
    response = client.put("/api/scheduler/schedule", json=[{"zone": "1", "day": "M", "duration": 1800}])  # 30 minutes in seconds
    assert response.status_code == 200
    assert response.json()["message"] == "Success"
    schedule = response.json()["schedule"]
    assert isinstance(schedule, list)
    assert len(schedule) > 0
    assert all(isinstance(item, dict) for item in schedule)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule)
