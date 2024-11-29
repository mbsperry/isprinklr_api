import logging, os, pytest, asyncio
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, patch
from typing import List

from context import isprinklr
from isprinklr.paths import logs_path
from isprinklr.schemas import SprinklerConfig, SprinklerCommand
from isprinklr.system_controller import SystemController
from isprinklr.system_status import SystemStatus

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

cwd = os.path.abspath(os.path.dirname(__file__))

# Test data
sprinklers: List[SprinklerConfig] = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Sidewalk"},
    {"zone": 4, "name": "Driveway"},    
]

@pytest.fixture
def mock_system_status(mocker):
    # Mock the sprinkler service to return our test data
    mocker.patch('isprinklr.sprinkler_service.read_sprinklers', return_value=sprinklers)
    mocker.patch('isprinklr.system_status.schedule_database.set_sprinklers')
    mocker.patch('isprinklr.system_status.schedule_database.load_database')
    system_status = SystemStatus()
    return system_status

@pytest.fixture
def mock_system_controller(mock_system_status, mocker):
    # Mock hardware interactions
    mocker.patch('isprinklr.system_controller.hunterserial.test_awake', return_value=True)
    mocker.patch('isprinklr.system_controller.hunterserial.start_zone', return_value=True)
    mocker.patch('isprinklr.system_controller.hunterserial.stop_zone', return_value=True)
    
    # Create controller with our mock status
    mocker.patch('isprinklr.system_controller.system_status', mock_system_status)
    system_controller = SystemController()
    return system_controller

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
async def test_start_sprinkler(mock_system_controller):
    sprinkler: SprinklerCommand = {"zone": 1, "duration": 300}  # 5 minutes in seconds
    assert await mock_system_controller.start_sprinkler(sprinkler) == True

@pytest.mark.asyncio
async def test_start_sprinkler_while_running(mock_system_controller):
    try: 
        sprinkler1: SprinklerCommand = {"zone": 1, "duration": 300}  # 5 minutes in seconds
        sprinkler2: SprinklerCommand = {"zone": 2, "duration": 300}  # 5 minutes in seconds
        await mock_system_controller.start_sprinkler(sprinkler1)
        await mock_system_controller.start_sprinkler(sprinkler2)
    except Exception as exc:
        assert str(exc) == "Failed to start zone 2, system already active. Active zone: 1"

@pytest.mark.asyncio
async def test_start_sprinkler_with_invalid_zone(mock_system_controller):
    try:
        sprinkler: SprinklerCommand = {"zone": 5, "duration": 300}  # 5 minutes in seconds
        await mock_system_controller.start_sprinkler(sprinkler)
    except ValueError as exc:
        assert str(exc) == "Zone 5 not found"

@pytest.mark.asyncio
async def test_stop_system(mock_system_controller):
    sprinkler: SprinklerCommand = {"zone": 1, "duration": 300}  # 5 minutes in seconds
    assert await mock_system_controller.start_sprinkler(sprinkler) == True
    assert await mock_system_controller.stop_system() == True
    assert mock_system_controller._timer_task is None

@pytest.mark.asyncio
async def test_zone_timer_auto_stop(mock_system_controller):
    """Test that the system automatically stops after duration elapses"""
    # Create a mock sleep that we can control
    sleep_complete = asyncio.Event()
    async def mock_sleep(duration):
        # Wait until the test signals it's time to complete
        await sleep_complete.wait()
    
    # Mock both sleep and hardware interactions
    with patch('isprinklr.system_controller.asyncio.sleep', new=mock_sleep), \
         patch('isprinklr.system_controller.hunterserial.test_awake', return_value=True), \
         patch('isprinklr.system_controller.hunterserial.start_zone', return_value=True), \
         patch('isprinklr.system_controller.hunterserial.stop_zone', return_value=True):
        
        # Start a sprinkler with a 5-minute duration
        sprinkler: SprinklerCommand = {"zone": 1, "duration": 300}
        await mock_system_controller.start_sprinkler(sprinkler)
        
        # Now let the sleep complete
        sleep_complete.set()
        # Wait for the timer task to finish
        if mock_system_controller._timer_task:
            await mock_system_controller._timer_task
        
        # Verify timer task is cleaned up
        assert mock_system_controller._timer_task is None

@pytest.mark.asyncio
async def test_run_zone_sequence_success(mock_system_controller):
    # Mock the required methods
    mock_system_controller.start_sprinkler = AsyncMock(return_value=True)
    mock_system_controller.stop_system = AsyncMock(return_value=True)

    # Mock asyncio.sleep at the system level
    with patch('isprinklr.system_controller.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence - durations in seconds
        zone_sequence = [[1, 60], [2, 120]]  # Two zones, 1 and 2 minutes in seconds
        
        # Run the sequence
        result = await mock_system_controller.run_zone_sequence(zone_sequence)
        
        assert result == True
        assert mock_system_controller.start_sprinkler.call_count == 2
        assert mock_system_controller.stop_system.call_count == 2
        
        # Verify the sequence of calls
        mock_system_controller.start_sprinkler.assert_any_call({"zone": 1, "duration": 60})
        mock_system_controller.start_sprinkler.assert_any_call({"zone": 2, "duration": 120})
        
        # Verify sleep durations (already in seconds)
        mock_sleep.assert_any_call(60)  # 1 minute in seconds
        mock_sleep.assert_any_call(120)  # 2 minutes in seconds
        assert mock_sleep.call_count == 2

@pytest.mark.asyncio
async def test_run_zone_sequence_start_failure(mock_system_controller):
    # Mock start_sprinkler to fail
    mock_system_controller.start_sprinkler = AsyncMock(side_effect=Exception("Failed to start zone"))
    mock_system_controller.stop_system = AsyncMock(return_value=True)

    # Mock asyncio.sleep at the system level
    with patch('isprinklr.system_controller.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence - durations in seconds
        zone_sequence = [[1, 60], [2, 60]]  # Two zones, 1 minute each in seconds
        
        # Run the sequence
        result = await mock_system_controller.run_zone_sequence(zone_sequence)
        
        assert result == False
        assert mock_system_controller.start_sprinkler.call_count == 1  # Should fail on first zone
        assert mock_system_controller.stop_system.call_count == 0  # Should not need to stop since start failed
        assert mock_sleep.call_count == 0  # Should not sleep at all

@pytest.mark.asyncio
async def test_run_zone_sequence_stop_failure(mock_system_controller):
    # Mock start_sprinkler to succeed but stop_system to fail
    mock_system_controller.start_sprinkler = AsyncMock(return_value=True)
    mock_system_controller.stop_system = AsyncMock(side_effect=Exception("Failed to stop zone"))

    # Mock asyncio.sleep at the system level
    with patch('isprinklr.system_controller.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Test sequence - durations in seconds
        zone_sequence = [[1, 60], [2, 60]]  # Two zones, 1 minute each in seconds
        
        # Run the sequence
        result = await mock_system_controller.run_zone_sequence(zone_sequence)
        
        assert result == False
        assert mock_system_controller.start_sprinkler.call_count == 1  # Should fail after first zone
        assert mock_system_controller.stop_system.call_count == 1  # Should attempt to stop once
        assert mock_sleep.call_count == 1  # Should sleep once for the first zone
