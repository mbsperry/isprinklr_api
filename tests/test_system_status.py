import logging, os, pytest, asyncio
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from context import isprinklr
from isprinklr.paths import logs_path
from isprinklr.schemas import ScheduleItem, SprinklerConfig, SprinklerCommand
from isprinklr.system_status import SystemStatus
import isprinklr.sprinkler_service
import isprinklr.schedule_service

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

cwd = os.path.abspath(os.path.dirname(__file__))

sprinklers: List[SprinklerConfig] = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Sidewalk"},
    {"zone": 4, "name": "Driveway"},    
]

schedule = [
    ScheduleItem(zone=1, day="M", duration=1800),  # 30 minutes in seconds
    ScheduleItem(zone=2, day="Tu", duration=1800),
    ScheduleItem(zone=3, day="W", duration=1800),
    ScheduleItem(zone=4, day="Th", duration=1800),
]

@pytest.fixture
def mock_system_status(mocker):
    mocker.patch('isprinklr.sprinkler_service.read_sprinklers', return_value=sprinklers)
    mocker.patch('isprinklr.schedule_service.ScheduleService.read_schedule', return_value=schedule)
    system_status = SystemStatus()
    return system_status

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

def test_get_status(mock_system_status):
    assert mock_system_status.get_status() == {
        "systemStatus": "inactive",
        "message": None,
        "active_zone": None,
        "duration": 0
    }

def test_get_sprinklers(mock_system_status):
    assert len(mock_system_status.sprinklers) == 4

def test_update_sprinklers_success(mock_system_status, mocker):
    new_sprinklers: List[SprinklerConfig] = [
        {"zone": 1, "name": "Updated Front"},
        {"zone": 2, "name": "Updated Back"}
    ]
    mocker.patch('isprinklr.sprinkler_service.write_sprinklers', return_value=True)
    result = mock_system_status.update_sprinklers(new_sprinklers)
    assert result == new_sprinklers
    assert mock_system_status._sprinklers == new_sprinklers

def test_update_sprinklers_validation_error(mock_system_status, mocker):
    invalid_sprinklers: List[SprinklerConfig] = [
        {"zone": 1, "name": "Duplicate Zone"},
        {"zone": 1, "name": "Duplicate Zone"}
    ]
    mocker.patch('isprinklr.sprinkler_service.write_sprinklers', 
                side_effect=ValueError("Validation Error: Duplicate zones in sprinklers"))
    with pytest.raises(ValueError, match="Validation Error: Duplicate zones in sprinklers"):
        mock_system_status.update_sprinklers(invalid_sprinklers)

def test_update_sprinklers_write_error(mock_system_status, mocker):
    new_sprinklers: List[SprinklerConfig] = [{"zone": 1, "name": "Test"}]
    mocker.patch('isprinklr.sprinkler_service.write_sprinklers', 
                side_effect=Exception("Failed to write file"))
    with pytest.raises(Exception, match="Failed to write file"):
        mock_system_status.update_sprinklers(new_sprinklers)

def test_get_status_while_running(mock_system_status):
    mock_system_status.update_status("active", None, 1, 300)  # 5 minutes in seconds
    status = mock_system_status.get_status()
    assert status["systemStatus"] == "active"
    assert status["active_zone"] == 1
    assert status["duration"] > 1

def test_duration_decreases_with_time(mock_system_status):
    """Test that the sprinkler duration decreases properly as time passes"""
    # Mock time to start at 1000
    current_time = 1000
    with patch('isprinklr.system_status.time.time', return_value=current_time):
        # Set status with 300 second duration
        mock_system_status.update_status("active", None, 1, 300)
        
        # Initial status should show full duration
        status = mock_system_status.get_status()
        assert status["duration"] == 300
        
        # Advance time by 100 seconds
        current_time += 100
        with patch('isprinklr.system_status.time.time', return_value=current_time):
            status = mock_system_status.get_status()
            assert status["duration"] == 200
            
        # Advance time by another 150 seconds
        current_time += 150
        with patch('isprinklr.system_status.time.time', return_value=current_time):
            status = mock_system_status.get_status()
            assert status["duration"] == 50
            
        # Advance time past duration
        current_time += 100
        with patch('isprinklr.system_status.time.time', return_value=current_time):
            status = mock_system_status.get_status()
            assert status["duration"] == 0
