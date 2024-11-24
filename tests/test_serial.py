import logging, os, pytest
import serial
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock, patch, call

from context import isprinklr
from isprinklr.paths import logs_path
import isprinklr.sprinklr_serial as sprinklr_serial

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Test data
MOCK_CONN_ID = b'\x01'  # Fixed connection ID for testing
MOCK_PORT = "/dev/ttyACM0"  # Match the actual port used in the code

# Mock config for consistent testing
MOCK_CONFIG = {
    "serial_port": MOCK_PORT,
    "log_level": "ERROR",
    "dummy_mode": "False"
}

def create_mock_serial():
    """Create a base mock serial port with common attributes"""
    mock = MagicMock(spec=serial.Serial)
    mock.write = MagicMock(return_value=8)  # Return typical packet length
    mock.flush = MagicMock()
    mock.close = MagicMock()
    return mock

@pytest.fixture(autouse=True)
def mock_sleep(mocker):
    """Mock sleep to speed up tests"""
    return mocker.patch('time.sleep', return_value=None)

@pytest.fixture(autouse=True)
def mock_config(mocker):
    """Mock config to ensure consistent test environment"""
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data=str(MOCK_CONFIG)))
    mocker.patch('json.load', return_value=MOCK_CONFIG)
    # Ensure DUMMY_MODE is False for tests
    mocker.patch.object(sprinklr_serial, 'DUMMY_MODE', False)
    # Ensure SERIAL_PORT is set correctly
    mocker.patch.object(sprinklr_serial, 'SERIAL_PORT', MOCK_PORT)
    return mock_open

@pytest.fixture
def mock_time(mocker):
    """Mock time for consistent connection IDs"""
    mock = mocker.patch('time.time')
    mock.return_value = 1  # Fixed time for consistent conn_id
    return mock

@pytest.fixture
def mock_serial_success(mocker):
    """Mock serial port with successful responses"""
    mock = create_mock_serial()
    
    # Track state for response generation
    mock.packets_written = []
    mock.read_count = 0
    
    def mock_inWaiting():
        # Return data available only for the first read after each write
        if mock.packets_written and mock.read_count < len(mock.packets_written):
            return 7
        return 0
    
    def mock_read(size=1):
        if size != 7 or not mock.packets_written:
            return b''
        
        # Get the last written packet
        last_packet = mock.packets_written[mock.read_count]
        mock.read_count += 1
        
        # Extract conn_id and calculate checksum
        conn_id = last_packet[1:2]
        checksum = sprinklr_serial.fletcher16(last_packet)
        
        # If it's a handshake packet (contains SYN)
        if sprinklr_serial.SYN in last_packet:
            return (
                sprinklr_serial.BEGIN +
                conn_id +
                sprinklr_serial.SYN +
                sprinklr_serial.ACK +
                checksum.to_bytes(2, byteorder='little') +
                sprinklr_serial.END
            )
        # For command packets
        else:
            return (
                sprinklr_serial.BEGIN +
                conn_id +
                sprinklr_serial.ACK +
                b'\x00' +
                checksum.to_bytes(2, byteorder='little') +
                sprinklr_serial.END
            )
    
    def mock_write_with_tracking(packet):
        mock.packets_written.append(packet)
        return len(packet)
    
    mock.write = MagicMock(side_effect=mock_write_with_tracking)
    mock.inWaiting = MagicMock(side_effect=mock_inWaiting)
    mock.read = MagicMock(side_effect=mock_read)
    return mocker.patch('serial.Serial', return_value=mock)

@pytest.fixture
def mock_serial_timeout(mocker):
    """Mock serial port that simulates timeout"""
    mock = create_mock_serial()
    mock.inWaiting = MagicMock(return_value=0)
    mock.read = MagicMock(return_value=b'')
    return mocker.patch('serial.Serial', return_value=mock)

@pytest.fixture
def mock_serial_bad_response(mocker):
    """Mock serial port that returns invalid responses"""
    mock = create_mock_serial()
    
    def mock_inWaiting():
        # Return data available only once
        if not hasattr(mock, 'data_sent'):
            mock.data_sent = True
            return 7
        return 0
    
    mock.inWaiting = MagicMock(side_effect=mock_inWaiting)
    mock.read = MagicMock(return_value=b'\x00' * 7)  # Invalid response
    return mocker.patch('serial.Serial', return_value=mock)

# Fletcher16 checksum tests
def test_fletcher16_empty():
    """Test Fletcher16 checksum with empty data"""
    result = sprinklr_serial.fletcher16(b'')
    assert isinstance(result, int)
    assert result == 0

def test_fletcher16_known_data():
    """Test Fletcher16 checksum with known data"""
    test_data = b'\x01\x02\x03'
    result = sprinklr_serial.fletcher16(test_data)
    assert isinstance(result, int)
    # Test consistency
    assert result == sprinklr_serial.fletcher16(test_data)

# Handshake tests
def test_handshake_success(mock_serial_success, mock_time):
    """Test successful handshake sequence"""
    arduino = serial.Serial(MOCK_PORT)
    result = sprinklr_serial.handshake(arduino, MOCK_CONN_ID)
    assert result == True
    assert arduino.write.call_count >= 1

def test_handshake_timeout(mock_serial_timeout, mock_time):
    """Test handshake timeout handling"""
    arduino = serial.Serial(MOCK_PORT)
    result = sprinklr_serial.handshake(arduino, MOCK_CONN_ID)
    assert result == False

def test_handshake_bad_response(mock_serial_bad_response, mock_time):
    """Test handling of invalid handshake response"""
    arduino = serial.Serial(MOCK_PORT)
    result = sprinklr_serial.handshake(arduino, MOCK_CONN_ID)
    assert result == False

# Zone control tests
def test_start_zone_success(mock_serial_success, mock_time):
    """Test successful start_zone command"""
    result = sprinklr_serial.start_zone(1, 10)
    assert result == True
    mock_serial_success.return_value.write.assert_called()

def test_start_zone_dummy_mode(mocker):
    """Test start_zone in dummy mode"""
    mocker.patch.object(sprinklr_serial, 'DUMMY_MODE', True)
    result = sprinklr_serial.start_zone(1, 10)
    assert result == True

def test_stop_zone_success(mock_serial_success, mock_time):
    """Test successful stop_zone command"""
    result = sprinklr_serial.stop_zone(1)
    assert result == True
    mock_serial_success.return_value.write.assert_called()

def test_stop_zone_dummy_mode(mocker):
    """Test stop_zone in dummy mode"""
    mocker.patch.object(sprinklr_serial, 'DUMMY_MODE', True)
    result = sprinklr_serial.stop_zone(1)
    assert result == True

# Error handling tests
def test_serial_connection_error(mocker):
    """Test handling of serial connection error"""
    # Create a mock Serial that raises IOError
    mock_serial = MagicMock(spec=serial.Serial)
    mock_serial.side_effect = IOError("Connection failed")
    mocker.patch('serial.Serial', mock_serial)
    
    # Mock the logger to prevent actual error logging and capture the message
    mock_logger = mocker.patch.object(sprinklr_serial.logger, 'error')
    
    try:
        result = sprinklr_serial.test_awake()
        pytest.fail("Expected IOError to be raised")
    except IOError as exc:
        # Verify the error was logged
        mock_logger.assert_called_with('sprinklr_serial: Caught file I/O error Connection failed')
        assert str(exc) == "Connection failed"

def test_write_command_timeout(mock_serial_timeout, mock_time):
    """Test command write timeout handling"""
    cmd = sprinklr_serial.START_SPRINKLER + b'\x01' + b'\x0A'
    result = sprinklr_serial.writeCmd(cmd)
    assert result == False

# Protocol tests
def test_test_awake_success(mock_serial_success, mock_time):
    """Test successful Arduino wake test"""
    result = sprinklr_serial.test_awake()
    assert result == True
    mock_serial_success.assert_called_with(MOCK_PORT, 9600, timeout=1)

def test_test_awake_dummy_mode(mocker):
    """Test Arduino wake test in dummy mode"""
    mocker.patch.object(sprinklr_serial, 'DUMMY_MODE', True)
    result = sprinklr_serial.test_awake()
    assert result == True

def test_packet_formation(mock_serial_success, mock_time):
    """Test correct packet formation"""
    arduino = serial.Serial(MOCK_PORT)
    cmd = sprinklr_serial.START_SPRINKLER + b'\x01' + b'\x0A'
    sprinklr_serial.writeCmd(cmd)
    
    # Verify packet structure
    assert mock_serial_success.return_value.write.called
    calls = mock_serial_success.return_value.write.call_args_list
    for call in calls:
        packet = call[0][0]
        assert packet.startswith(sprinklr_serial.BEGIN)
        assert packet.endswith(sprinklr_serial.END)
        assert len(packet) >= 8  # Minimum packet length
