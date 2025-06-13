import json, logging, os, pytest
from logging.handlers import RotatingFileHandler
from unittest.mock import mock_open, patch

from context import isprinklr
from isprinklr.paths import logs_path
from isprinklr.schedule_database import ScheduleDatabase

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

good_sprinklers = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Side Lawn"},
    {"zone": 4, "name": "Rear Lawn"},
]

good_schedules = {
    "schedules": [
        {
            "schedule_name": "Default Schedule",
            "schedule_items": [
                {"zone": 1, "day": "M:W:F", "duration": 600},
                {"zone": 2, "day": "Tu:Th", "duration": 900},
            ]
        },
        {
            "schedule_name": "Summer Schedule",
            "schedule_items": [
                {"zone": 3, "day": "EO", "duration": 1200},
                {"zone": 4, "day": "ALL", "duration": 300},
            ]
        }
    ],
    "active_schedule": "Default Schedule"
}

@pytest.fixture
def mock_json_file(mocker):
    """Mock the JSON file operations"""
    mock_file = mock_open(read_data=json.dumps(good_schedules))
    mocker.patch('builtins.open', mock_file)
    return mock_file

@pytest.fixture
def db():
    """Create a fresh ScheduleDatabase instance"""
    return ScheduleDatabase()

def test_init():
    """Test initialization creates empty database"""
    db = ScheduleDatabase()
    assert db.sprinklers is None
    assert len(db.schedules) == 0
    assert db.active_schedule_name is None

def test_set_sprinklers(db):
    """Test setting sprinkler configurations"""
    db.set_sprinklers(good_sprinklers)
    assert db.sprinklers == good_sprinklers

def test_load_without_sprinklers(db):
    """Test loading database without setting sprinklers first"""
    with pytest.raises(ValueError, match="Sprinklers must be set before loading database"):
        db.load_database()

def test_load_with_valid_json(mock_json_file, db):
    """Test loading with valid JSON data"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    assert len(db.schedules) == 2
    assert db.active_schedule_name == "Default Schedule"
    assert db.schedules[0]["schedule_name"] == "Default Schedule"
    assert db.schedules[1]["schedule_name"] == "Summer Schedule"

def test_load_with_missing_file(mocker, db):
    """Test loading when file doesn't exist"""
    mocker.patch('builtins.open', side_effect=FileNotFoundError)
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    assert len(db.schedules) == 0
    assert db.active_schedule_name is None

def test_load_with_invalid_json(mocker, db):
    """Test loading with invalid JSON data"""
    mock_file = mock_open(read_data="invalid json")
    mocker.patch('builtins.open', mock_file)
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    assert len(db.schedules) == 0
    assert db.active_schedule_name is None

def test_get_schedule(mock_json_file, db):
    """Test getting a schedule by name"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    schedule = db.get_schedule("Default Schedule")
    assert schedule["schedule_name"] == "Default Schedule"
    assert len(schedule["schedule_items"]) == 2

    with pytest.raises(ValueError, match="Schedule 'Nonexistent' not found"):
        db.get_schedule("Nonexistent")

def test_get_active_schedule(mock_json_file, db):
    """Test getting the active schedule"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    schedule = db.get_active_schedule()
    assert schedule["schedule_name"] == "Default Schedule"
    assert len(schedule["schedule_items"]) == 2

    # Test when no active schedule
    db.active_schedule_name = None
    with pytest.raises(ValueError, match="No active schedule"):
        db.get_active_schedule()

def test_update_schedule_without_sprinklers(db):
    """Test updating schedule without setting sprinklers"""
    with pytest.raises(ValueError, match="Sprinklers must be set before updating schedule"):
        db.update_schedule({})

def test_update_schedule(mock_json_file, db, caplog):
    """Test updating an existing schedule"""
    caplog.set_level(logging.DEBUG)
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    
    new_schedule = {
        "schedule_name": "Default Schedule",  # Update existing schedule
        "schedule_items": [
            {"zone": 1, "day": "ALL", "duration": 300},
            {"zone": 2, "day": "EO", "duration": 600},
        ]
    }
    
    updated = db.update_schedule(new_schedule)
    assert updated["schedule_name"] == "Default Schedule"
    assert len(updated["schedule_items"]) == 2
    assert updated["schedule_items"][0]["day"] == "ALL"
    assert updated["schedule_items"][1]["day"] == "EO"
    assert len(db.schedules) == 2  # Total number of schedules should remain the same
    
    # Test updating non-existent schedule
    non_existent_schedule = new_schedule.copy()
    non_existent_schedule["schedule_name"] = "Nonexistent"
    with pytest.raises(ValueError, match="Schedule 'Nonexistent' not found"):
        db.update_schedule(non_existent_schedule)

def test_add_schedule_without_sprinklers(db):
    """Test adding schedule without setting sprinklers"""
    with pytest.raises(ValueError, match="Sprinklers must be set before adding schedule"):
        db.add_schedule({})

def test_add_schedule(mock_json_file, db, caplog):
    """Test adding a new schedule"""
    caplog.set_level(logging.DEBUG)
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    
    new_schedule = {
        "schedule_name": "New Schedule",
        "schedule_items": [
            {"zone": 1, "day": "ALL", "duration": 300},
            {"zone": 2, "day": "EO", "duration": 600},
        ]
    }
    
    added = db.add_schedule(new_schedule)
    assert added["schedule_name"] == "New Schedule"
    assert len(db.schedules) == 3  # Total number of schedules should increase
    
    # Test adding schedule with existing name
    with pytest.raises(ValueError, match="Schedule 'New Schedule' already exists"):
        db.add_schedule(new_schedule)

def test_write_schedule_file(mock_json_file, db):
    """Test writing schedules to file"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    assert db.write_schedule_file() == True
    
    # Verify write was called with correct data
    write_call = mock_json_file().write.call_args[0][0]
    written_data = json.loads(write_call)
    assert "schedules" in written_data
    assert "active_schedule" in written_data
    assert len(written_data["schedules"]) == 2

def test_validate_schedule_data_without_sprinklers(db):
    """Test schedule data validation without sprinklers set"""
    with pytest.raises(ValueError, match="Sprinklers must be set before validating schedule data"):
        db.validate_schedule_data(good_schedules)

def test_validate_schedule_data(mock_json_file, db):
    """Test schedule data validation"""
    db.set_sprinklers(good_sprinklers)
    
    # Test valid data
    assert db.validate_schedule_data(good_schedules) == True
    
    # Test missing required keys
    with pytest.raises(ValueError, match="Missing required keys"):
        db.validate_schedule_data({"schedules": good_schedules["schedules"]})
    
    # Test invalid schedules type
    invalid_data = good_schedules.copy()
    invalid_data["schedules"] = "invalid"
    with pytest.raises(ValueError, match="Schedules must be a list"):
        db.validate_schedule_data(invalid_data)
    
    # Test invalid active_schedule type
    invalid_data = good_schedules.copy()
    invalid_data["active_schedule"] = 1  # Should be string or None
    with pytest.raises(ValueError, match="Active schedule must be a string or None"):
        db.validate_schedule_data(invalid_data)
    
    # Test non-existent active_schedule name
    invalid_data = good_schedules.copy()
    invalid_data["active_schedule"] = "Nonexistent"
    with pytest.raises(ValueError, match="Active schedule name does not exist"):
        db.validate_schedule_data(invalid_data)

def test_delete_schedule(mock_json_file, db):
    """Test deleting a schedule"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()
    
    # Verify initial state
    assert len(db.schedules) == 2
    assert db.active_schedule_name == "Default Schedule"
    
    # Test deleting non-active schedule
    assert db.delete_schedule("Summer Schedule") == True
    assert len(db.schedules) == 1
    assert db.active_schedule_name == "Default Schedule"  # Active schedule should remain unchanged
    
    # Verify file was updated
    write_call = mock_json_file().write.call_args[0][0]
    written_data = json.loads(write_call)
    assert len(written_data["schedules"]) == 1
    assert written_data["active_schedule"] == "Default Schedule"

    # Test deleting non-existent schedule
    with pytest.raises(ValueError, match="Schedule 'Nonexistent' not found"):
        db.delete_schedule("Nonexistent")
    
def test_delete_active_schedule(mock_json_file, db):
    """Test deleting the active schedule"""
    db.set_sprinklers(good_sprinklers)
    db.load_database()

    # Verify initial state
    assert len(db.schedules) == 2
    assert db.active_schedule_name == "Default Schedule"

    # Test deleting active schedule
    assert db.delete_schedule("Default Schedule") == True
    assert len(db.schedules) == 1
    assert db.active_schedule_name is None
