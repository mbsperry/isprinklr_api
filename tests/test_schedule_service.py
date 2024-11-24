import logging, os, pytest
from logging.handlers import RotatingFileHandler

from context import isprinklr
import isprinklr.schedule_service
import isprinklr.sprinkler_service
from isprinklr.paths import logs_path, data_path
from isprinklr.schemas import ScheduleItem

logging.basicConfig(handlers=[RotatingFileHandler(logs_path + '/test.log', maxBytes=1024*1024, backupCount=1, mode='a')],
                    datefmt='%m-%d-%Y %H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

cwd = os.path.abspath(os.path.dirname(__file__))

bad_sprinklers = {
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
        {"zone": 1, "name": "This is a very long name that should not be allowed"}
    ],
    "empty_sprinklers": []
}

# Test schedules with durations in seconds
bad_schedules = {
    "duplicate_zones": [
        {"zone": 1, "day": "M", "duration": 600},  # 10 minutes in seconds
        {"zone": 1, "day": "Tu", "duration": 600},
    ],
    "invalid_days": [
        {"zone": 1, "day": "Mon", "duration": 600},
        {"zone": 2, "day": "Tu", "duration": 600},
    ],
    "duration_too_long": [
        {"zone": 1, "day": "M", "duration": 7800},  # Over 2 hours (7200 seconds)
        {"zone": 2, "day": "Tu", "duration": 600},
    ],
    "duration_too_short": [
        {"zone": 1, "day": "M", "duration": -1},
        {"zone": 2, "day": "Tu", "duration": 600},
    ],
    "zone_not_in_sprinklers": [
        {"zone": 1, "day": "M", "duration": 600},
        {"zone": 5, "day": "Tu", "duration": 600},
    ],
}

good_sprinklers = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Side Lawn"},
    {"zone": 4, "name": "Rear Lawn"},
]

@pytest.fixture()
def mock_schedule_path(mocker):
    return mocker.patch('isprinklr.schedule_service.data_path', cwd + '/data') 


def test_schedule(mock_schedule_path):
    schedule = isprinklr.schedule_service.ScheduleService(isprinklr.sprinkler_service.read_sprinklers(cwd + '/data')).schedule
    assert isinstance(schedule, list)
    assert len(schedule) == 4
    assert all(isinstance(item, dict) for item in schedule)
    assert all("zone" in item and "day" in item and "duration" in item for item in schedule)

def test_sprinklers():
    sprinklers = isprinklr.sprinkler_service.read_sprinklers(cwd + '/data')
    assert isinstance(sprinklers, list)
    assert len(sprinklers) == 4
    assert all(isinstance(item, dict) for item in sprinklers)
    assert all("zone" in item and "name" in item for item in sprinklers)

def test_spinkler_validation():
    try:
        isprinklr.sprinkler_service.validate_sprinklers(bad_sprinklers["too_many_zones"])
    except ValueError:
        assert True
    try:
        isprinklr.sprinkler_service.validate_sprinklers(bad_sprinklers["duplicate_zones"])
    except ValueError:
        assert True
    try:
        isprinklr.sprinkler_service.validate_sprinklers(bad_sprinklers["duplicate_names"])
    except ValueError:
        assert True
    try:
        isprinklr.sprinkler_service.validate_sprinklers(bad_sprinklers["empty_sprinklers"])
    except ValueError:
        assert True
    try:
        isprinklr.sprinkler_service.validate_sprinklers(bad_sprinklers["long_name"])
    except ValueError:
        assert True

def test_schedule_validation():
    try:
        isprinklr.schedule_service.ScheduleService.validate_schedule(bad_schedules["duplicate_zones"], good_sprinklers)
    except ValueError:
        assert True
    try:
        isprinklr.schedule_service.ScheduleService.validate_schedule(bad_schedules["invalid_days"], good_sprinklers)
    except ValueError:
        assert True
    try:
        isprinklr.schedule_service.ScheduleService.validate_schedule(bad_schedules["duration_too_long"], good_sprinklers)
    except ValueError:
        assert True
    try:
        isprinklr.schedule_service.ScheduleService.validate_schedule(bad_schedules["duration_too_short"], good_sprinklers)
    except ValueError:
        assert True
    try:
        isprinklr.schedule_service.ScheduleService.validate_schedule(bad_schedules["zone_not_in_sprinklers"], good_sprinklers)
    except ValueError:
        assert True

def test_write_sprinklers(mocker):
    mock = mocker.patch('isprinklr.sprinkler_service.pd.DataFrame.to_csv', return_value=None)
    isprinklr.sprinkler_service.write_sprinklers(data_path, good_sprinklers)
    mock.assert_called_once_with(data_path + '/sprinklers.csv', index=False)

def test_write_sprinklers_file_write_error(mocker):
    mock = mocker.patch('isprinklr.sprinkler_service.pd.DataFrame.to_csv', side_effect=IOError("File write error"))
    try:
        isprinklr.sprinkler_service.write_sprinklers(data_path, good_sprinklers)
    except IOError:
        assert True
    else:
        pytest.fail("Expected IOError")

@pytest.fixture()
def schedule_service(mocker, mock_schedule_path):
    schedule_service = isprinklr.schedule_service.ScheduleService(good_sprinklers)
    return schedule_service

def test_update_schedule(mocker, schedule_service):
    new_schedule = [
        {"zone": 1, "day": "M", "duration": 300},  # 5 minutes in seconds
        {"zone": 2, "day": "W", "duration": 1200},  # 20 minutes in seconds
    ]
    mock = mocker.patch('isprinklr.schedule_service.pd.DataFrame.to_csv', return_value=None)
    try:
        schedule_service.update_schedule(new_schedule)
    except Exception as exc:
        raise
    mock.assert_called_once_with(cwd + '/data/schedule.csv', index=False)
    assert schedule_service.schedule == new_schedule


def test_update_schedule_file_write_error(mocker, schedule_service):
    new_schedule = [
        {"zone": 1, "day": "M", "duration": 300},  # 5 minutes in seconds
        {"zone": 2, "day": "W", "duration": 1200},  # 20 minutes in seconds
    ]
    mock = mocker.patch('isprinklr.schedule_service.pd.DataFrame.to_csv', side_effect=IOError("File write error"))
    try:
        schedule_service.update_schedule(new_schedule)
    except IOError:
        assert True
    else:
        pytest.fail("Expected IOError")

def test_get_scheduled_zones(schedule_service):
    # Set up test schedule with durations in seconds
    test_schedule = [
        {"zone": 1, "day": "M", "duration": 600},      # Monday, 10 minutes
        {"zone": 2, "day": "ALL", "duration": 900},    # Every day, 15 minutes
        {"zone": 3, "day": "EO", "duration": 1200},    # Odd days, 20 minutes
        {"zone": 4, "day": "NONE", "duration": 1500},  # Never, 25 minutes
        {"zone": 5, "day": "M:W:F", "duration": 600},  # M:W:F, 10 minutes
    ]
    schedule_service.schedule = test_schedule

    # Test Monday on odd day (01/02/23)
    monday_zones = schedule_service.get_scheduled_zones("010223")
    assert len(monday_zones) == 3
    assert {"zone": 1, "duration": 600} in monday_zones  # Monday
    assert {"zone": 2, "duration": 900} in monday_zones  # ALL
    assert {"zone": 5, "duration": 600} in monday_zones  # M:W:F

    # Test Tuesday on odd day (01/03/23)
    tuesday_zones = schedule_service.get_scheduled_zones("010323")
    assert len(tuesday_zones) == 2
    assert {"zone": 2, "duration": 900} in tuesday_zones  # ALL
    assert {"zone": 3, "duration": 1200} in tuesday_zones  # EO

    # Test Wednesday on even day (01/04/23)
    wednesday_zones = schedule_service.get_scheduled_zones("010423")
    assert len(wednesday_zones) == 2
    assert {"zone": 5, "duration": 600} in wednesday_zones  # M:W:F
    assert {"zone": 2, "duration": 900} in wednesday_zones  # ALL 

    # Test invalid date format
    invalid_zones = schedule_service.get_scheduled_zones("invalid")
    assert len(invalid_zones) == 0
