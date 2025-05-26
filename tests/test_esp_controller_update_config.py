import pytest
from unittest.mock import patch, MagicMock

from context import isprinklr
import isprinklr.esp_controller as esp_controller

# Test data
MOCK_ESP_IP = "192.168.1.100"
NEW_MOCK_ESP_IP = "192.168.1.200"

@pytest.fixture(autouse=True)
def reset_esp_controller():
    """Reset ESP controller configuration before each test"""
    # Save original values
    original_ip = esp_controller.ESP_CONTROLLER_IP
    original_dummy_mode = esp_controller.DUMMY_MODE
    original_base_url = esp_controller.BASE_URL
    
    # Yield control to the test
    yield
    
    # Restore original values after test
    esp_controller.ESP_CONTROLLER_IP = original_ip
    esp_controller.DUMMY_MODE = original_dummy_mode
    esp_controller.BASE_URL = original_base_url

def test_update_config_ip_only():
    """Test updating only the IP address"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Update only the IP
    result = esp_controller.update_config(new_ip=NEW_MOCK_ESP_IP)
    
    # Check the result
    assert result["ESP_controller_IP"] == NEW_MOCK_ESP_IP
    assert result["dummy_mode"] == False
    assert result["BASE_URL"] == f"http://{NEW_MOCK_ESP_IP}"
    
    # Check that globals were updated
    assert esp_controller.ESP_CONTROLLER_IP == NEW_MOCK_ESP_IP
    assert esp_controller.DUMMY_MODE == False
    assert esp_controller.BASE_URL == f"http://{NEW_MOCK_ESP_IP}"

def test_update_config_dummy_mode_only():
    """Test updating only the dummy mode"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Update only the dummy mode
    result = esp_controller.update_config(new_dummy_mode=True)
    
    # Check the result
    assert result["ESP_controller_IP"] == MOCK_ESP_IP
    assert result["dummy_mode"] == True
    assert result["BASE_URL"] == f"http://{MOCK_ESP_IP}"
    
    # Check that globals were updated
    assert esp_controller.ESP_CONTROLLER_IP == MOCK_ESP_IP
    assert esp_controller.DUMMY_MODE == True
    assert esp_controller.BASE_URL == f"http://{MOCK_ESP_IP}"

def test_update_config_both():
    """Test updating both IP and dummy mode"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Update both
    result = esp_controller.update_config(new_ip=NEW_MOCK_ESP_IP, new_dummy_mode=True)
    
    # Check the result
    assert result["ESP_controller_IP"] == NEW_MOCK_ESP_IP
    assert result["dummy_mode"] == True
    assert result["BASE_URL"] == f"http://{NEW_MOCK_ESP_IP}"
    
    # Check that globals were updated
    assert esp_controller.ESP_CONTROLLER_IP == NEW_MOCK_ESP_IP
    assert esp_controller.DUMMY_MODE == True
    assert esp_controller.BASE_URL == f"http://{NEW_MOCK_ESP_IP}"

def test_update_config_safety_check():
    """Test the safety check for empty IP and dummy mode False"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = ""
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = ""
    
    # Update with empty IP and dummy mode False
    result = esp_controller.update_config()
    
    # Safety check should force dummy mode to True
    assert result["ESP_controller_IP"] == ""
    assert result["dummy_mode"] == True
    assert result["BASE_URL"] == ""
    
    # Check that globals were updated
    assert esp_controller.ESP_CONTROLLER_IP == ""
    assert esp_controller.DUMMY_MODE == True
    assert esp_controller.BASE_URL == ""

def test_update_config_no_change():
    """Test when no changes are made"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Update with same values
    result = esp_controller.update_config(new_ip=MOCK_ESP_IP, new_dummy_mode=False)
    
    # No changes should have been made
    assert result["ESP_controller_IP"] == MOCK_ESP_IP
    assert result["dummy_mode"] == False
    assert result["BASE_URL"] == f"http://{MOCK_ESP_IP}"
    
    # Check that globals were not changed
    assert esp_controller.ESP_CONTROLLER_IP == MOCK_ESP_IP
    assert esp_controller.DUMMY_MODE == False
    assert esp_controller.BASE_URL == f"http://{MOCK_ESP_IP}"

@patch('isprinklr.esp_controller.logger')
def test_logging_when_config_changes(mock_logger):
    """Test that logging occurs when config changes"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Update both
    esp_controller.update_config(new_ip=NEW_MOCK_ESP_IP, new_dummy_mode=True)
    
    # Check that logging occurred
    mock_logger.info.assert_any_call("ESP controller configuration updated.")
    mock_logger.info.assert_any_call(f"New ESP Controller IP: '{NEW_MOCK_ESP_IP}'")
    mock_logger.info.assert_any_call(f"New ESP Controller DUMMY_MODE: {True}")

@patch('isprinklr.esp_controller.logger')
def test_no_logging_when_no_changes(mock_logger):
    """Test that no logging occurs when no changes are made"""
    # Set initial values
    esp_controller.ESP_CONTROLLER_IP = MOCK_ESP_IP
    esp_controller.DUMMY_MODE = False
    esp_controller.BASE_URL = f"http://{MOCK_ESP_IP}"
    
    # Reset mock logger
    mock_logger.reset_mock()
    
    # Update with same values
    esp_controller.update_config(new_ip=MOCK_ESP_IP, new_dummy_mode=False)
    
    # Verify info logs about configuration update were not called
    mock_logger.info.assert_not_called()
