import logging, os, pytest
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from context import isprinklr
from isprinklr.paths import logs_path
from isprinklr.schemas import ScheduleItem, SprinklerConfig, Sprinkler
from isprinklr.system import SystemStatus
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
    ScheduleItem(zone=1, day="M", duration=30),
    ScheduleItem(zone=2, day="Tu", duration=30),
    ScheduleItem(zone=3, day="W", duration=30),
    ScheduleItem(zone=4, day="Th", duration=30),
]

@pytest.fixture
def mock_system_status(mocker):
    mocker.patch('isprinklr.sprinkler_service.read_sprinklers', return_value=sprinklers)
    mocker.patch('isprinklr.schedule_service.ScheduleService.read_schedule', return_value=schedule)
    system_status = SystemStatus()
    return system_status

def test_get_status(mock_system_status):
    assert mock_system_status.get_status() == {
        "systemStatus": "inactive",
        "message": None,
        "active_zone": None,
        "duration": 0
    }

def test_get_sprinklers(mock_system_status):
    assert len(mock_system_status.get_sprinklers()) == 4

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

@pytest.mark.asyncio
async def test_start_sprinkler(mock_system_status):
    sprinkler: Sprinkler = {"zone": 1, "duration": 5}
    assert await mock_system_status.start_sprinkler(sprinkler) == True

@pytest.mark.asyncio
async def test_get_status_while_running(mock_system_status):
    sprinkler: Sprinkler = {"zone": 1, "duration": 5}
    assert await mock_system_status.start_sprinkler(sprinkler) == True
    status = mock_system_status.get_status()
    assert status["systemStatus"] == "active"
    assert status["active_zone"] == 1
    assert status["duration"] > 1

@pytest.mark.asyncio
async def test_start_sprinkler_while_running(mock_system_status):
    try: 
        sprinkler1: Sprinkler = {"zone": 1, "duration": 5}
        sprinkler2: Sprinkler = {"zone": 2, "duration": 5}
        await mock_system_status.start_sprinkler(sprinkler1)
        await mock_system_status.start_sprinkler(sprinkler2)
    except Exception as exc:
        assert str(exc) == "Failed to start zone 2, system already active. Active zone: 1"

@pytest.mark.asyncio
async def test_start_sprinkler_with_invalid_zone(mock_system_status):
    try:
        sprinkler: Sprinkler = {"zone": 5, "duration": 5}
        await mock_system_status.start_sprinkler(sprinkler)
    except ValueError as exc:
        assert str(exc) == "Zone 5 not found"

@pytest.mark.asyncio
async def test_stop_system(mock_system_status):
    sprinkler: Sprinkler = {"zone": 1, "duration": 5}
    assert await mock_system_status.start_sprinkler(sprinkler) == True
    assert mock_system_status.stop_system() == True
    status = mock_system_status.get_status()
    assert status["systemStatus"] == "inactive"
    assert status["active_zone"] == None
    assert status["duration"] == 0
    assert status["message"] == None

@pytest.mark.asyncio
async def test_run_zone_sequence_success(mock_system_status):
    # Mock the required methods
    mock_system_status.start_sprinkler = AsyncMock(return_value=True)
    mock_system_status.stop_system = MagicMock(return_value=True)
    mock_system_status._active_zone = None

    # Mock asyncio.sleep
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence
        zone_sequence = [[1, 1], [2, 2]]  # Two zones, 1 and 2 minutes
        
        # Run the sequence
        result = await mock_system_status.run_zone_sequence(zone_sequence)
        
        assert result == True
        assert mock_system_status.start_sprinkler.call_count == 2
        assert mock_system_status.stop_system.call_count == 2
        
        # Verify the sequence of calls
        mock_system_status.start_sprinkler.assert_any_call({"zone": 1, "duration": 1})
        mock_system_status.start_sprinkler.assert_any_call({"zone": 2, "duration": 2})
        
        # Verify sleep durations (minutes converted to seconds)
        mock_sleep.assert_any_call(60)  # 1 minute for first zone
        mock_sleep.assert_any_call(120)  # 2 minutes for second zone
        assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_run_zone_sequence_start_failure(mock_system_status):
    # Mock start_sprinkler to fail
    mock_system_status.start_sprinkler = AsyncMock(side_effect=Exception("Failed to start zone"))
    mock_system_status.stop_system = MagicMock(return_value=True)
    mock_system_status._active_zone = None

    # Mock asyncio.sleep
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence
        zone_sequence = [[1, 1], [2, 1]]
        
        # Run the sequence
        result = await mock_system_status.run_zone_sequence(zone_sequence)
        
        assert result == False
        assert mock_system_status.start_sprinkler.call_count == 1  # Should fail on first zone
        assert mock_system_status.stop_system.call_count == 0  # Should not need to stop since start failed
        assert mock_sleep.call_count == 0  # Should not sleep at all

@pytest.mark.asyncio
async def test_run_zone_sequence_stop_failure(mock_system_status):
    # Mock start_sprinkler to succeed but stop_system to fail
    mock_system_status.start_sprinkler = AsyncMock(return_value=True)
    mock_system_status.stop_system = MagicMock(side_effect=Exception("Failed to stop zone"))
    mock_system_status._active_zone = 1

    # Mock asyncio.sleep
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence
        zone_sequence = [[1, 1], [2, 1]]
        
        # Run the sequence
        result = await mock_system_status.run_zone_sequence(zone_sequence)
        
        assert result == False
        assert mock_system_status.start_sprinkler.call_count == 1  # Should fail after first zone
        assert mock_system_status.stop_system.call_count == 1  # Should attempt to stop once
        assert mock_sleep.call_count == 1  # Should sleep once for the first zone
