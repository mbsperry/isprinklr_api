from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pytest
import asyncio

from context import isprinklr
from isprinklr.system_status import system_status, schedule_database, SystemStatus
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

@pytest.fixture(autouse=True)
def cleanup_tasks():
    """Clean up any pending asyncio tasks after each test"""
    yield
    # Clean up any pending tasks after each test
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in tasks:
                task.cancel()
    except RuntimeError:
        # No event loop running, nothing to clean up
        pass

def test_get_schedules(mocker):
    mocker.patch.object(schedule_database, 'schedules', [test_schedule])
    response = client.get("/api/scheduler/schedules")
    assert response.status_code == 200
    schedules = response.json()
    assert isinstance(schedules, list)
    assert len(schedules) == 1
    assert schedules[0] == test_schedule

def test_get_schedule_by_name(mocker):
    mocker.patch.object(schedule_database, 'get_schedule', return_value=test_schedule)
    response = client.get("/api/scheduler/schedule/Test Schedule")
    assert response.status_code == 200
    schedule = response.json()
    assert schedule == test_schedule

def test_get_schedule_by_name_not_found(mocker):
    mocker.patch.object(schedule_database, 'get_schedule', 
                       side_effect=ValueError("Schedule 'Nonexistent' not found"))
    response = client.get("/api/scheduler/schedule/Nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_get_active_schedule(mocker):
    mocker.patch.object(schedule_database, 'get_active_schedule', return_value=test_schedule)
    response = client.get("/api/scheduler/active")
    assert response.status_code == 200
    schedule = response.json()
    assert schedule == test_schedule

def test_get_active_schedule_none(mocker):
    mocker.patch.object(schedule_database, 'get_active_schedule', 
                       side_effect=ValueError("No active schedule"))
    response = client.get("/api/scheduler/active")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_set_active_schedule(mocker):
    get_schedule_mock = mocker.patch.object(schedule_database, 'get_schedule', 
                                          return_value=test_schedule)
    write_mock = mocker.patch.object(schedule_database, 'write_schedule_file')
    
    response = client.put("/api/scheduler/active/Test Schedule")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["active_schedule"] == test_schedule
    assert schedule_database.active_schedule == "Test Schedule"
    
    get_schedule_mock.assert_called_once_with("Test Schedule")
    write_mock.assert_called_once()

def test_set_active_schedule_not_found(mocker):
    mocker.patch.object(schedule_database, 'get_schedule', 
                       side_effect=ValueError("Schedule 'Nonexistent' not found"))
    response = client.put("/api/scheduler/active/Nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

def test_create_schedule(mocker):
    add_mock = mocker.patch.object(schedule_database, 'add_schedule', return_value=test_schedule)
    response = client.post("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["schedule"] == test_schedule
    add_mock.assert_called_once_with(test_schedule)

def test_create_schedule_validation_error(mocker):
    mocker.patch.object(schedule_database, 'add_schedule', 
                       side_effect=ValueError("Schedule validation failed"))
    response = client.post("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_update_schedule(mocker):
    mocker.patch.object(schedule_database, 'update_schedule', return_value=test_schedule)
    response = client.put("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    assert result["schedule"] == test_schedule

def test_update_schedule_validation_error(mocker):
    mocker.patch.object(schedule_database, 'update_schedule', 
                       side_effect=ValueError("Schedule validation failed"))
    response = client.put("/api/scheduler/schedule", json=test_schedule)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_delete_schedule(mocker):
    delete_mock = mocker.patch.object(schedule_database, 'delete_schedule', return_value=True)
    response = client.delete("/api/scheduler/schedule/Test Schedule")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Success"
    delete_mock.assert_called_once_with("Test Schedule")

def test_delete_schedule_not_found(mocker):
    mocker.patch.object(schedule_database, 'delete_schedule', 
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

def test_run_schedule_success(mocker):
    """Test successful schedule run by mocking the manager_run_schedule function"""
    # Expected result from manager_run_schedule
    expected_result = {
        "message": "Started running schedule",
        "zones": [
            {"zone": 1, "duration": 60},
            {"zone": 2, "duration": 120}
        ]
    }
    
    # Mock the manager_run_schedule function
    mock_run_schedule = AsyncMock(return_value=expected_result)
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/schedule/Test Schedule/run")
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert result == expected_result
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with("Test Schedule")

def test_run_schedule_value_error(mocker):
    """Test schedule not found error by mocking manager_run_schedule"""
    # Mock the manager_run_schedule function to raise ValueError
    mock_run_schedule = AsyncMock(side_effect=ValueError("Schedule 'Nonexistent' not found"))
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/schedule/Nonexistent/run")
        
        # Verify response
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "not found" in response.json()["detail"]
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with("Nonexistent")

def test_run_schedule_runtime_error(mocker):
    """Test system already running error by mocking manager_run_schedule"""
    # Mock the manager_run_schedule function to raise RuntimeError
    mock_run_schedule = AsyncMock(side_effect=RuntimeError("System is already running zone 1"))
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/schedule/Test Schedule/run")
        
        # Verify response
        assert response.status_code == 409
        assert "detail" in response.json()
        assert "System is already running zone 1" in response.json()["detail"]
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with("Test Schedule")

def test_run_schedule_unexpected_error(mocker):
    """Test unexpected error handling by mocking manager_run_schedule"""
    # Mock the manager_run_schedule function to raise an unexpected exception
    mock_run_schedule = AsyncMock(side_effect=Exception("Unexpected error"))
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/schedule/Test Schedule/run")
        
        # Verify response
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Internal server error" in response.json()["detail"]
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with("Test Schedule")

def test_run_active_schedule_success(mocker):
    """Test successful active schedule run by mocking manager_run_schedule"""
    # Expected result from manager_run_schedule
    expected_result = {
        "message": "Started running active schedule",
        "zones": [
            {"zone": 1, "duration": 60},
            {"zone": 2, "duration": 120}
        ]
    }
    
    # Mock the manager_run_schedule function
    mock_run_schedule = AsyncMock(return_value=expected_result)
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/active/run")
        
        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert result == expected_result
        
        # Verify mock was called correctly - should be called with no arguments
        mock_run_schedule.assert_awaited_once_with()

def test_run_active_schedule_no_active(mocker):
    """Test no active schedule error by mocking manager_run_schedule"""
    # Mock the manager_run_schedule function to raise ValueError
    mock_run_schedule = AsyncMock(side_effect=ValueError("No active schedule set"))
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/active/run")
        
        # Verify response
        assert response.status_code == 404
        assert "detail" in response.json()
        assert "No active schedule set" in response.json()["detail"]
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with()

def test_run_active_schedule_runtime_error(mocker):
    """Test system already running error by mocking manager_run_schedule"""
    # Mock the manager_run_schedule function to raise RuntimeError
    mock_run_schedule = AsyncMock(side_effect=RuntimeError("System is already running zone 1"))
    with patch('isprinklr.routers.scheduler.manager_run_schedule', mock_run_schedule):
        # Call the endpoint
        response = client.post("/api/scheduler/active/run")
        
        # Verify response
        assert response.status_code == 409
        assert "detail" in response.json()
        assert "System is already running zone 1" in response.json()["detail"]
        
        # Verify mock was called correctly
        mock_run_schedule.assert_awaited_once_with()
