import logging, os, pytest
import requests
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock, patch, call

from context import isprinklr
from isprinklr.paths import logs_path
import isprinklr.esp_controller as esp_controller

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Test data
MOCK_ESP_IP = "192.168.1.100"  # Mock IP for testing
MOCK_BASE_URL = f"http://{MOCK_ESP_IP}"

# Mock config for consistent testing
MOCK_CONFIG = {
    "ESP_controller_IP": MOCK_ESP_IP,
    "log_level": "ERROR",
    "dummy_mode": "False"
}

@pytest.fixture(autouse=True)
def mock_config(mocker):
    """Mock config to ensure consistent test environment"""
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data=str(MOCK_CONFIG)))
    mocker.patch('json.load', return_value=MOCK_CONFIG)
    # Ensure DUMMY_MODE is False for tests
    mocker.patch.object(esp_controller, 'DUMMY_MODE', False)
    # Ensure ESP_CONTROLLER_IP is set correctly
    mocker.patch.object(esp_controller, 'ESP_CONTROLLER_IP', MOCK_ESP_IP)
    # Ensure BASE_URL is set correctly
    mocker.patch.object(esp_controller, 'BASE_URL', MOCK_BASE_URL)
    return mock_open

# Mock response fixtures
@pytest.fixture
def mock_status_response():
    """Create a mock successful status response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "ok",
        "uptime_ms": 123456,
        "chip": {
            "model": "ESP32-S3",
            "revision": 1,
            "cores": 2
        },
        "network": {
            "connected": True,
            "type": "Ethernet",
            "ip": MOCK_ESP_IP
        }
    }
    return mock_response

@pytest.fixture
def mock_start_success_response():
    """Create a mock successful start response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "started",
        "zone": 5,
        "minutes": 10
    }
    return mock_response

@pytest.fixture
def mock_stop_success_response():
    """Create a mock successful stop response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "stopped",
        "zone": 5
    }
    return mock_response

@pytest.fixture
def mock_error_response():
    """Create a mock error response"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "status": "error",
        "error": "Invalid zone"
    }
    mock_response.text = '{"status": "error", "error": "Invalid zone"}'
    return mock_response

# Test cases for test_awake
def test_test_awake_success(mocker, mock_status_response):
    """Test a successful status check"""
    mocker.patch('requests.get', return_value=mock_status_response)
    result = esp_controller.test_awake()
    # Now test_awake returns the full status data instead of just True
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "ok"
    assert "uptime_ms" in result
    assert "chip" in result
    assert "network" in result
    requests.get.assert_called_once_with(f"{MOCK_BASE_URL}/api/status", timeout=5)

def test_test_awake_error_status(mocker, mock_error_response):
    """Test handling of error status code"""
    mocker.patch('requests.get', return_value=mock_error_response)
    with pytest.raises(Exception) as exc_info:
        esp_controller.test_awake()
    assert "ESP controller returned error status" in str(exc_info.value)

def test_test_awake_connection_error(mocker):
    """Test handling of connection error"""
    mocker.patch('requests.get', side_effect=requests.exceptions.RequestException("Connection refused"))
    with pytest.raises(Exception) as exc_info:
        esp_controller.test_awake()
    assert "ESP controller connection error" in str(exc_info.value)

def test_test_awake_dummy_mode(mocker):
    """Test behavior in dummy mode"""
    mocker.patch.object(esp_controller, 'DUMMY_MODE', True)
    # Should not even try to make a request in dummy mode
    mock_get = mocker.patch('requests.get')
    result = esp_controller.test_awake()
    # Should return a dummy status dictionary in dummy mode, not just True
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "ok"
    assert "dummy_mode" in result
    assert result["dummy_mode"] == True
    mock_get.assert_not_called()

# Test cases for start_zone
def test_start_zone_success(mocker, mock_start_success_response):
    """Test successful start zone request"""
    mocker.patch('requests.post', return_value=mock_start_success_response)
    result = esp_controller.start_zone(5, 10)
    assert result == True
    requests.post.assert_called_once_with(
        f"{MOCK_BASE_URL}/api/start", 
        json={"zone": 5, "minutes": 10}, 
        timeout=5
    )

def test_start_zone_error_response(mocker, mock_error_response):
    """Test handling of error response for start zone"""
    mocker.patch('requests.post', return_value=mock_error_response)
    with pytest.raises(IOError) as exc_info:
        esp_controller.start_zone(5, 10)
    assert "Command Failed" in str(exc_info.value)

def test_start_zone_connection_error(mocker):
    """Test handling of connection error for start zone"""
    mocker.patch('requests.post', side_effect=requests.exceptions.RequestException("Connection refused"))
    with pytest.raises(IOError) as exc_info:
        esp_controller.start_zone(5, 10)
    assert "Communication Error" in str(exc_info.value)

def test_start_zone_dummy_mode(mocker):
    """Test start zone in dummy mode"""
    mocker.patch.object(esp_controller, 'DUMMY_MODE', True)
    mock_post = mocker.patch('requests.post')
    result = esp_controller.start_zone(5, 10)
    assert result == True
    mock_post.assert_not_called()

# Test cases for stop_zone
def test_stop_zone_success(mocker, mock_stop_success_response):
    """Test successful stop zone request"""
    mocker.patch('requests.post', return_value=mock_stop_success_response)
    result = esp_controller.stop_zone(5)
    assert result == True
    requests.post.assert_called_once_with(
        f"{MOCK_BASE_URL}/api/stop", 
        json={"zone": 5}, 
        timeout=5
    )

def test_stop_zone_error_response(mocker, mock_error_response):
    """Test handling of error response for stop zone"""
    mocker.patch('requests.post', return_value=mock_error_response)
    with pytest.raises(IOError) as exc_info:
        esp_controller.stop_zone(5)
    assert "Command Failed" in str(exc_info.value)

def test_stop_zone_connection_error(mocker):
    """Test handling of connection error for stop zone"""
    mocker.patch('requests.post', side_effect=requests.exceptions.RequestException("Connection refused"))
    with pytest.raises(IOError) as exc_info:
        esp_controller.stop_zone(5)
    assert "Communication Error" in str(exc_info.value)

def test_stop_zone_dummy_mode(mocker):
    """Test stop zone in dummy mode"""
    mocker.patch.object(esp_controller, 'DUMMY_MODE', True)
    mock_post = mocker.patch('requests.post')
    result = esp_controller.stop_zone(5)
    assert result == True
    mock_post.assert_not_called()

# Edge cases
def test_unexpected_response_format(mocker):
    """Test handling of unexpected response format"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"unknown_key": "value"}  # Missing expected keys
    
    mocker.patch('requests.post', return_value=mock_response)
    with pytest.raises(IOError) as exc_info:
        esp_controller.start_zone(5, 10)
    assert "Unexpected response" in str(exc_info.value)

def test_json_parse_error(mocker):
    """Test handling of JSON parse error in response"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.text = "Not JSON"
    
    mocker.patch('requests.post', return_value=mock_response)
    with pytest.raises(IOError):
        esp_controller.start_zone(5, 10)
