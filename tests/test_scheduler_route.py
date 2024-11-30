from fastapi.testclient import TestClient

from context import isprinklr
from isprinklr.system_status import SystemStatus
import isprinklr.system_status

from isprinklr.main import app

client = TestClient(app)

test_schedule = {
    "schedule_name": "Test Schedule",
    "schedule_items": [
        {"zone": 1, "day": "EO", "duration": 60},
        {"zone": 2, "day": "ALL", "duration": 120},
        {"zone": 3, "day": "M:W:F", "duration": 180},
        {"zone": 4, "day": "Tu:Th", "duration": 240}
    ]
}

def test_get_schedules(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'schedules', [test_schedule])
    response = client.get("/api/scheduler/schedules")
    assert response.status_code == 200
    schedules = response.json()
    assert isinstance(schedules, list)
    assert len(schedules) == 1
    assert schedules[0] == test_schedule

def test_get_schedule_by_name(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'get_schedule', return_value=test_schedule)
    response = client.get("/api/scheduler/schedule/Test Schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert schedule == test_schedule

def test_get_schedule_by_name_not_found(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'get_schedule', 
                       side_effect=ValueError("Schedule 'Nonexistent' not found"))
    response = client.get("/api/scheduler/schedule/Nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_get_active_schedule(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'get_active_schedule', return_value=test_schedule)
    response = client.get("/api/scheduler/active")
    assert response.status_code == 200
    schedule = response.json()
    assert schedule == test_schedule

def test_get_active_schedule_none(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'get_active_schedule', 
                       side_effect=ValueError("No active schedule"))
    response = client.get("/api/scheduler/active")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_set_active_schedule(mocker):
    get_schedule_mock = mocker.patch.object(isprinklr.system_status.schedule_database, 'get_schedule', 
                                          return_value=test_schedule)
    write_mock = mocker.patch.object(isprinklr.system_status.schedule_database, 'write_schedule_file')
    
    response = client.put("/api/scheduler/active/Test Schedule")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["active_schedule"] == test_schedule
    assert isprinklr.system_status.schedule_database.active_schedule_name == "Test Schedule"
    
    get_schedule_mock.assert_called_once_with("Test Schedule")
    write_mock.assert_called_once()

def test_set_active_schedule_not_found(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'get_schedule', 
                       side_effect=ValueError("Schedule 'Nonexistent' not found"))
    response = client.put("/api/scheduler/active/Nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_create_schedule(mocker):
    add_mock = mocker.patch.object(isprinklr.system_status.schedule_database, 'add_schedule', return_value=test_schedule)
    response = client.post("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["schedule"] == test_schedule
    add_mock.assert_called_once_with(test_schedule)

def test_create_schedule_validation_error(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'add_schedule', 
                       side_effect=ValueError("Schedule validation failed"))
    response = client.post("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_update_schedule(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'update_schedule', return_value=test_schedule)
    response = client.put("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["schedule"] == test_schedule

def test_update_schedule_validation_error(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'update_schedule', 
                       side_effect=ValueError("Schedule validation failed"))
    response = client.put("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_delete_schedule(mocker):
    delete_mock = mocker.patch.object(isprinklr.system_status.schedule_database, 'delete_schedule', return_value=True)
    response = client.delete("/api/scheduler/schedule/Test Schedule")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    delete_mock.assert_called_once_with("Test Schedule")

def test_delete_schedule_not_found(mocker):
    mocker.patch.object(isprinklr.system_status.schedule_database, 'delete_schedule', 
                       side_effect=ValueError("Schedule 'Nonexistent' not found"))
    response = client.delete("/api/scheduler/schedule/Nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

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
