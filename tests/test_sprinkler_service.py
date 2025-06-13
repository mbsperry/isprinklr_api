import logging
import os
import pytest
import json # Added
from unittest import mock # Added
from logging.handlers import RotatingFileHandler

from context import isprinklr # type: ignore
from isprinklr.paths import logs_path
import isprinklr.sprinkler_service
from isprinklr.schemas import SprinklerConfig # For type hinting if needed

logging.basicConfig(handlers=[RotatingFileHandler(os.path.join(logs_path, 'test.log'), maxBytes=1024*1024, backupCount=1, mode='a')], # Used os.path.join
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Test data
valid_sprinklers: list[SprinklerConfig] = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Side Yard"},
]

invalid_sprinklers_data = { 
    "too_many_zones": [
        {"zone": i, "name": f"Zone {i}"} for i in range(1, 14)
    ],
    "duplicate_zones": [
        {"zone": 1, "name": "Front Lawn"},
        {"zone": 1, "name": "Back Lawn"},
    ],
    "duplicate_names": [
        {"zone": 1, "name": "Front Lawn"},
        {"zone": 2, "name": "Front Lawn"},
    ],
    "long_name": [
        {"zone": 1, "name": "This is a very long name that should definitely not be allowed in the system"}
    ],
    "empty_sprinklers": [] 
}

def test_validate_valid_sprinklers():
    """Test that valid sprinkler configurations pass validation"""
    assert isprinklr.sprinkler_service.validate_sprinklers(valid_sprinklers) is True

def test_validate_too_many_zones():
    """Test that too many zones raises ValueError"""
    with pytest.raises(ValueError, match="Too many sprinklers defined"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers_data["too_many_zones"])

def test_validate_duplicate_zones():
    """Test that duplicate zones raises ValueError"""
    with pytest.raises(ValueError, match="Duplicate zones in sprinklers"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers_data["duplicate_zones"])

def test_validate_duplicate_names():
    """Test that duplicate names raises ValueError"""
    with pytest.raises(ValueError, match="Duplicate names in sprinklers"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers_data["duplicate_names"])

def test_validate_long_name():
    """Test that names > 30 characters raises ValueError"""
    with pytest.raises(ValueError, match="Name is too long"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers_data["long_name"])

def test_validate_empty_sprinklers():
    """Test that empty sprinkler list raises ValueError"""
    with pytest.raises(ValueError, match="No sprinklers defined"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers_data["empty_sprinklers"])

# Read Tests
@mock.patch('isprinklr.sprinkler_service.json.load')
@mock.patch('isprinklr.sprinkler_service.open', new_callable=mock.mock_open)
def test_read_sprinklers_success(mock_open_file, mock_json_load):
    """Test successful sprinkler data reading from JSON"""
    mock_json_load.return_value = valid_sprinklers
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    mock_open_file.assert_called_once_with(os.path.join("/test/path", "sprinklers.json"), "r")
    mock_json_load.assert_called_once()
    assert isinstance(result, list)
    assert result == valid_sprinklers # Verifies content and length

@mock.patch('isprinklr.sprinkler_service.open', side_effect=FileNotFoundError("File not found"))
def test_read_sprinklers_file_not_found(mock_open_file):
    """Test handling of FileNotFoundError when reading sprinklers.json"""
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    mock_open_file.assert_called_once_with(os.path.join("/test/path", "sprinklers.json"), "r")
    assert isinstance(result, list)
    assert len(result) == 0

@mock.patch('isprinklr.sprinkler_service.json.load', side_effect=json.JSONDecodeError("Decode error", "doc", 0))
@mock.patch('isprinklr.sprinkler_service.open', new_callable=mock.mock_open)
def test_read_sprinklers_json_decode_error(mock_open_file, mock_json_load):
    """Test handling of JSONDecodeError when reading sprinklers.json"""
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    mock_open_file.assert_called_once_with(os.path.join("/test/path", "sprinklers.json"), "r")
    mock_json_load.assert_called_once()
    assert isinstance(result, list)
    assert len(result) == 0

@mock.patch('isprinklr.sprinkler_service.json.load')
@mock.patch('isprinklr.sprinkler_service.open', new_callable=mock.mock_open)
def test_read_sprinklers_invalid_data_structure(mock_open_file, mock_json_load):
    """Test handling of invalid data structure (e.g., not a list) in sprinklers.json"""
    mock_json_load.return_value = {"sprinklers": valid_sprinklers} # Simulate a dict instead of a list
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    assert isinstance(result, list)
    assert len(result) == 0

@mock.patch('isprinklr.sprinkler_service.json.load')
@mock.patch('isprinklr.sprinkler_service.open', new_callable=mock.mock_open)
def test_read_sprinklers_validation_error(mock_open_file, mock_json_load):
    """Test handling of data that fails validate_sprinklers"""
    mock_json_load.return_value = invalid_sprinklers_data["duplicate_zones"]
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    assert isinstance(result, list)
    assert len(result) == 0


# Write Tests
def test_write_sprinklers_success(tmp_path):
    """Test successful sprinkler data writing to JSON using tmp_path"""
    data_path = tmp_path
    sprinklers_file = data_path / "sprinklers.json"
    
    assert isprinklr.sprinkler_service.write_sprinklers(str(data_path), valid_sprinklers) is True
    
    assert sprinklers_file.exists()
    with open(sprinklers_file, "r") as f:
        written_data = json.load(f)
    assert written_data == valid_sprinklers

@mock.patch('isprinklr.sprinkler_service.json.dump')
@mock.patch('isprinklr.sprinkler_service.open', new_callable=mock.mock_open)
def test_write_sprinklers_invalid_data(mock_open_file, mock_json_dump):
    """Test that invalid data raises ValueError before writing and json.dump is not called"""
    with pytest.raises(ValueError, match="Duplicate zones in sprinklers"): # Or other validation error
        isprinklr.sprinkler_service.write_sprinklers("/test/path", invalid_sprinklers_data["duplicate_zones"])
    
    mock_open_file.assert_not_called()
    mock_json_dump.assert_not_called()

@mock.patch('isprinklr.sprinkler_service.open', side_effect=IOError("File write error"))
def test_write_sprinklers_file_error(mock_open_file):
    """Test handling of file write errors (IOError)"""
    with pytest.raises(IOError, match="File write error"):
        isprinklr.sprinkler_service.write_sprinklers("/test/path", valid_sprinklers)
    
    # Check that open was attempted with the correct path and mode
    mock_open_file.assert_called_once_with(os.path.join("/test/path", "sprinklers.json"), "w")
