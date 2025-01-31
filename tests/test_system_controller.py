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
    # Create a controllable sleep
    sleep_complete = asyncio.Event()
    async def controlled_sleep(duration):
        # Signal that sleep was called and wait for test to complete it
        await sleep_complete.wait()
    
    # Mock the sleep
    with patch('isprinklr.system_controller.asyncio.sleep', new=controlled_sleep):
        # Test sequence - durations in seconds
        zones = [
            {"zone": 1, "duration": 60},  # 1 minute
            {"zone": 2, "duration": 120}   # 2 minutes
        ]
        
        # Run the sequence in the background
        sequence_task = asyncio.create_task(mock_system_controller.run_zone_sequence(zones))
        
        # Let the first zone's sleep complete
        sleep_complete.set()
        await asyncio.sleep(0.1)  # Give time for the sleep to actually complete
        await mock_system_controller.stop_system()  # This will properly update system status
        sleep_complete.clear()  # Reset for next zone
        
        # Let the second zone's timer complete
        sleep_complete.set()
        
        # Wait for sequence to complete
        await sequence_task
        
        # Verify cleanup
        assert mock_system_controller._sequence_task is None
        # Timer task should be cleaned up after sequence completion
        assert mock_system_controller._timer_task is None

@pytest.mark.asyncio
async def test_run_zone_sequence_start_failure(mock_system_controller):
    """Test that zone sequence raises error when start_sprinkler fails"""
    # Mock start_sprinkler to fail
    mock_system_controller.start_sprinkler = AsyncMock(side_effect=Exception("Failed to start zone"))

    # Test sequence - durations in seconds
    zones = [
        {"zone": 1, "duration": 60},  # 1 minute
        {"zone": 2, "duration": 60}   # 1 minute
    ]
    
    # Run the sequence and expect exception
    with pytest.raises(Exception, match="Failed to start zone"):
        await mock_system_controller.run_zone_sequence(zones)
    
    assert mock_system_controller.start_sprinkler.call_count == 1  # Should fail on first zone
    assert mock_system_controller._sequence_task is None
    assert mock_system_controller._timer_task is None

@pytest.mark.asyncio
async def test_stop_system_during_sequence(mock_system_controller):
    """Test that stopping the system during a sequence raises CancelledError and cleans up"""
    # Create a controllable sleep
    sleep_event = asyncio.Event()
    sleep_started = asyncio.Event()
    async def controlled_sleep(duration):
        sleep_started.set()  # Signal that sleep was called
        await sleep_event.wait()  # Wait for test to signal completion
    
    # Mock the sleep
    with patch('isprinklr.system_controller.asyncio.sleep', new=controlled_sleep):
        # Start a sequence
        zones = [
            {"zone": 1, "duration": 60},
            {"zone": 2, "duration": 60}
        ]
        
        # Start the sequence in the background
        sequence_task = asyncio.create_task(mock_system_controller.run_zone_sequence(zones))
        
        # Wait for the first sleep to start
        await sleep_started.wait()
        
        # Stop the system
        await mock_system_controller.stop_system()
        
        # Allow sleep to complete
        sleep_event.set()
        
        # Wait for sequence to raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await sequence_task
        
        # Verify cleanup
        assert mock_system_controller._sequence_task is None
        assert mock_system_controller._timer_task is None

@pytest.mark.asyncio
async def test_sequence_cancelled_mid_zone(mock_system_controller):
    """Test that cancelling a sequence mid-zone raises CancelledError and cleans up"""
    # Create a controllable sleep
    sleep_event = asyncio.Event()
    sleep_started = asyncio.Event()
    async def controlled_sleep(duration):
        sleep_started.set()  # Signal that sleep was called
        await sleep_event.wait()  # Wait for test to signal completion
    
    # Mock the sleep
    with patch('isprinklr.system_controller.asyncio.sleep', new=controlled_sleep):
        # Start a sequence
        zones = [
            {"zone": 1, "duration": 60},
            {"zone": 2, "duration": 60}
        ]
        
        # Start the sequence in the background
        sequence_task = asyncio.create_task(mock_system_controller.run_zone_sequence(zones))
        
        # Wait for the first sleep to start
        await sleep_started.wait()
        
        # Stop the system mid-zone
        await mock_system_controller.stop_system()
        
        # Allow sleep to complete
        sleep_event.set()
        
        # Wait for sequence to raise CancelledError
        with pytest.raises(asyncio.CancelledError):
            await sequence_task
        
        # Verify cleanup
        assert mock_system_controller._sequence_task is None
        assert mock_system_controller._timer_task is None
