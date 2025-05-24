import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from context import isprinklr
from isprinklr.scheduler_manager import run_schedule, automated_schedule_runner, setup_scheduler
from isprinklr.system_status import SystemStatus
import isprinklr.system_status
from isprinklr.system_controller import system_controller

# Test data
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
async def cleanup_tasks():
    yield
    # Clean up any pending tasks after each test
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_run_schedule_success():
    """Test running a schedule by name successfully"""
    # Mock dependencies
    scheduled_zones = [
        {"zone": 1, "duration": 60},
        {"zone": 2, "duration": 120}
    ]
    
    with patch.object(isprinklr.system_status.schedule_database, 'get_schedule', return_value=test_schedule), \
         patch('isprinklr.scheduler_manager.get_scheduled_zones', return_value=scheduled_zones), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None), \
         patch.object(system_controller, 'run_zone_sequence', new_callable=AsyncMock, return_value=True):
         
        # Execute the function
        result = await run_schedule("Test Schedule")
        
        # Verify results
        assert result["message"] == "Started running schedule"
        assert result["zones"] == scheduled_zones

@pytest.mark.asyncio
async def test_run_active_schedule_success():
    """Test running the active schedule successfully"""
    # Mock dependencies
    scheduled_zones = [
        {"zone": 1, "duration": 60},
        {"zone": 2, "duration": 120}
    ]
    
    # Setup mocks for directly getting the active schedule
    with patch.object(isprinklr.system_status.schedule_database, 'get_active_schedule', 
                    return_value={"schedule_name": "Test Schedule"}), \
        patch('isprinklr.scheduler_manager.run_schedule_helper', 
              new_callable=AsyncMock, return_value=(scheduled_zones, False)), \
        patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None), \
        patch('isprinklr.scheduler_manager.create_task') as mock_create_task:
        
        # Execute the function
        result = await run_schedule()  # No schedule name means use active schedule
        
        # Verify results
        assert result["message"] == "Started running active schedule"
        assert result["zones"] == scheduled_zones

@pytest.mark.asyncio
async def test_run_schedule_no_zones_today():
    """Test running a schedule with no zones for today"""
    with patch.object(isprinklr.system_status.schedule_database, 'get_schedule', return_value=test_schedule), \
         patch('isprinklr.scheduler_manager.get_scheduled_zones', return_value=[]), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None):
         
        # Execute the function
        result = await run_schedule("Test Schedule")
        
        # Verify results
        assert result["message"] == "No zones scheduled for today"
        assert result["zones"] == []

@pytest.mark.asyncio
async def test_run_schedule_system_busy():
    """Test running a schedule when system is already busy"""
    with patch.object(isprinklr.system_status.schedule_database, 'get_schedule', return_value=test_schedule), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=1):
         
        # Execute the function and expect RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            await run_schedule("Test Schedule")
        
        # Verify error message
        assert "System is already running zone 1" in str(exc_info.value)

@pytest.mark.asyncio
async def test_run_schedule_not_found():
    """Test running a schedule that doesn't exist"""
    with patch.object(isprinklr.system_status.schedule_database, 'get_schedule', 
                      side_effect=ValueError("Schedule 'NonExistent' not found")), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None):
         
        # Execute the function and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await run_schedule("NonExistent")
        
        # Verify error message
        assert "not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_run_active_schedule_no_zones():
    """Test running the active schedule with no zones for today"""
    # Mock the components directly
    with patch.object(isprinklr.system_status.schedule_database, 'get_active_schedule', 
                    return_value={"schedule_name": "Test Schedule"}), \
         patch('isprinklr.scheduler_manager.run_schedule_helper', 
               new_callable=AsyncMock, return_value=([], True)), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None):
         
        # Execute the function
        result = await run_schedule()  # No schedule name means use active schedule
        
        # Verify results
        assert result["message"] == "No zones scheduled for today"
        assert result["zones"] == []

@pytest.mark.asyncio
async def test_run_active_schedule_not_set():
    """Test running the active schedule when none is set"""
    # The issue is that None active_schedule gets passed to run_schedule_helper 
    # which then fails when trying to get the schedule
    with patch('isprinklr.scheduler_manager.schedule_database') as mock_db, \
         patch('isprinklr.scheduler_manager.run_schedule_helper',
              side_effect=ValueError("No active schedule set")), \
         patch.object(isprinklr.system_status.SystemStatus, 'active_zone', new=None):
        
        # Set up the mock to return None when accessing active_schedule
        mock_db.active_schedule = None
         
        # Execute the function and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await run_schedule()  # No name means use active schedule
        
        # Verify error message
        assert "No active schedule" in str(exc_info.value)

@pytest.mark.asyncio
async def test_automated_schedule_runner_scheduling_disabled():
    """Test automated_schedule_runner when scheduling is disabled"""
    with patch.object(isprinklr.system_status.SystemStatus, 'schedule_on_off', False), \
         patch('isprinklr.scheduler_manager.run_schedule', new_callable=AsyncMock) as mock_run_schedule:
         
        # Execute the function
        await automated_schedule_runner()
        
        # Verify that run_schedule was not called
        mock_run_schedule.assert_not_called()

@pytest.mark.asyncio
async def test_automated_schedule_runner_scheduling_enabled():
    """Test automated_schedule_runner when scheduling is enabled"""
    with patch.object(isprinklr.system_status.SystemStatus, 'schedule_on_off', True), \
         patch('isprinklr.scheduler_manager.run_schedule', new_callable=AsyncMock) as mock_run_schedule:
         
        # Execute the function
        await automated_schedule_runner()
        
        # Verify that run_schedule was called once
        mock_run_schedule.assert_called_once()

def test_setup_scheduler():
    """Test that the scheduler is set up correctly"""
    with patch('isprinklr.scheduler_manager.scheduler') as mock_scheduler:
        # Configure the mock scheduler to report not running
        mock_scheduler.running = False
        # Execute the function
        setup_scheduler(hour=6, minute=30)
        
        # Verify scheduler operations
        mock_scheduler.remove_all_jobs.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
