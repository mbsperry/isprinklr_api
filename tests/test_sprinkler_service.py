import logging, os, pytest
import pandas as pd
from logging.handlers import RotatingFileHandler

from context import isprinklr
from isprinklr.paths import logs_path
import isprinklr.sprinkler_service

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

cwd = os.path.abspath(os.path.dirname(__file__))

# Test data
valid_sprinklers = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Side Yard"},
]

invalid_sprinklers = {
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

# Fixtures
@pytest.fixture
def mock_csv_read(mocker):
    return mocker.patch('pandas.read_csv')

@pytest.fixture
def mock_csv_write(mocker):
    return mocker.patch('pandas.DataFrame.to_csv')

# Validation Tests
def test_validate_valid_sprinklers():
    """Test that valid sprinkler configurations pass validation"""
    assert isprinklr.sprinkler_service.validate_sprinklers(valid_sprinklers) == True

def test_validate_too_many_zones():
    """Test that too many zones raises ValueError"""
    with pytest.raises(ValueError, match="Too many sprinklers defined"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers["too_many_zones"])

def test_validate_duplicate_zones():
    """Test that duplicate zones raises ValueError"""
    with pytest.raises(ValueError, match="Duplicate zones in sprinklers"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers["duplicate_zones"])

def test_validate_duplicate_names():
    """Test that duplicate names raises ValueError"""
    with pytest.raises(ValueError, match="Duplicate names in sprinklers"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers["duplicate_names"])

def test_validate_long_name():
    """Test that names > 30 characters raises ValueError"""
    with pytest.raises(ValueError, match="Name is too long"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers["long_name"])

def test_validate_empty_sprinklers():
    """Test that empty sprinkler list raises ValueError"""
    with pytest.raises(ValueError, match="No sprinklers defined"):
        isprinklr.sprinkler_service.validate_sprinklers(invalid_sprinklers["empty_sprinklers"])

# Read Tests
def test_read_sprinklers_success(mock_csv_read):
    """Test successful sprinkler data reading"""
    mock_df = pd.DataFrame(valid_sprinklers)
    mock_csv_read.return_value = mock_df
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    assert isinstance(result, list)
    assert len(result) == len(valid_sprinklers)
    assert all(isinstance(item, dict) for item in result)
    assert all("zone" in item and "name" in item for item in result)
    mock_csv_read.assert_called_once_with("/test/path/sprinklers.csv", usecols=["zone", "name"])

def test_read_sprinklers_file_error(mock_csv_read):
    """Test handling of file read errors"""
    mock_csv_read.side_effect = Exception("File read error")
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    assert isinstance(result, list)
    assert len(result) == 0

def test_read_sprinklers_invalid_data(mock_csv_read):
    """Test handling of invalid data in CSV"""
    mock_df = pd.DataFrame(invalid_sprinklers["duplicate_zones"])
    mock_csv_read.return_value = mock_df
    
    result = isprinklr.sprinkler_service.read_sprinklers("/test/path")
    
    assert isinstance(result, list)
    assert len(result) == 0

# Write Tests
def test_write_sprinklers_success(mock_csv_write):
    """Test successful sprinkler data writing"""
    assert isprinklr.sprinkler_service.write_sprinklers("/test/path", valid_sprinklers) == True
    mock_csv_write.assert_called_once_with("/test/path/sprinklers.csv", index=False)

def test_write_sprinklers_invalid_data(mock_csv_write):
    """Test that invalid data raises ValueError before writing"""
    with pytest.raises(ValueError):
        isprinklr.sprinkler_service.write_sprinklers("/test/path", invalid_sprinklers["duplicate_zones"])
    
    mock_csv_write.assert_not_called()

def test_write_sprinklers_file_error(mock_csv_write):
    """Test handling of file write errors"""
    mock_csv_write.side_effect = Exception("File write error")
    
    with pytest.raises(Exception):
        isprinklr.sprinkler_service.write_sprinklers("/test/path", valid_sprinklers)
