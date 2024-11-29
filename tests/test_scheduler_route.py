from fastapi.testclient import TestClient

from context import isprinklr
from isprinklr.system_status import SystemStatus, schedule_database

from isprinklr.main import app

client = TestClient(app)

test_schedule = {
    "sched_id": 1,
    "schedule_name": "Test Schedule",
    "schedule_items": [
        {"zone": 1, "day": "EO", "duration": 60},
        {"zone": 2, "day": "ALL", "duration": 120},
        {"zone": 3, "day": "M:W:F", "duration": 180},
        {"zone": 4, "day": "Tu:Th", "duration": 240}
    ]
}

def test_get_schedule(mocker):
    mocker.patch.object(schedule_database, 'get_active_schedule', return_value=test_schedule)
    response = client.get("/api/scheduler/schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert isinstance(schedule, list)
    assert len(schedule) == 4
    assert all(isinstance(item, dict) for item in schedule)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule)

def test_get_schedule_empty(mocker):
    mocker.patch.object(schedule_database, 'get_active_schedule', side_effect=ValueError("No active schedule"))
    response = client.get("/api/scheduler/schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert isinstance(schedule, list)
    assert len(schedule) == 0

def test_get_schedule_on_off(mocker):
    mocker.patch.object(SystemStatus, 'schedule_on_off', new_callable=mocker.PropertyMock, 
                       return_value=True)
    response = client.get("/api/scheduler/on_off")
    assert response.status_code == 200
    schedule_on_off = response.json()
    assert isinstance(schedule_on_off, dict)
    assert isinstance(schedule_on_off["schedule_on_off"], bool)
    assert schedule_on_off["schedule_on_off"] == True

def test_update_schedule_on_off(mocker):
    response = client.put("/api/scheduler/on_off", params={"schedule_on_off": False})
    assert response.status_code == 200
    assert response.json() == {"schedule_on_off": False}

def test_update_schedule(mocker):
    new_schedule = {
        "sched_id": 1,
        "schedule_name": "Updated Schedule",
        "schedule_items": [
            {"zone": 1, "day": "M", "duration": 1800}, 
            {"zone": 2, "day": "W", "duration": 1800}
        ]
    }
    mocker.patch.object(schedule_database, 'update_schedule', return_value=new_schedule)
    response = client.put("/api/scheduler/schedule", json=new_schedule)
    assert response.status_code == 200
    assert response.json()["message"] == "Success"
    schedule = response.json()["schedule"]
    assert isinstance(schedule, dict)
    assert "sched_id" in schedule
    assert "schedule_name" in schedule
    assert "schedule_items" in schedule
    schedule_items = schedule["schedule_items"]
    assert isinstance(schedule_items, list)
    assert len(schedule_items) == 2
    assert all(isinstance(item, dict) for item in schedule_items)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule_items)

def test_update_schedule_validation_error(mocker):
    new_schedule = {
        "sched_id": 1,
        "schedule_name": "Invalid Schedule",
        "schedule_items": [
            {"zone": 999, "day": "INVALID", "duration": -1}
        ]
    }
    mocker.patch.object(schedule_database, 'update_schedule', side_effect=ValueError("Invalid schedule"))
    response = client.put("/api/scheduler/schedule", json=new_schedule)
    assert response.status_code == 400
    assert "detail" in response.json()
