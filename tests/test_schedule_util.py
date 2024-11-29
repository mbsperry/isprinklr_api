import logging, os, pytest
from logging.handlers import RotatingFileHandler
from copy import deepcopy

from context import isprinklr
from isprinklr.paths import logs_path
from isprinklr.schemas import ScheduleItem
from isprinklr.schedule_util import validate_schedule, validate_schedule_list, get_scheduled_zones

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

good_schedule = [
    {"zone": 1, "day": "M:W:F", "duration": 600},  # 10 minutes, MWF
    {"zone": 2, "day": "Tu:Th", "duration": 900},  # 15 minutes, TTh
    {"zone": 3, "day": "EO", "duration": 1200},    # 20 minutes, Every Other day
    {"zone": 4, "day": "ALL", "duration": 300},    # 5 minutes, Every day
]

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

def test_schedule_validation():
    """Test validation of individual schedules"""
    # Test valid schedule
    assert validate_schedule(good_schedule, good_sprinklers) == True

    try:
        validate_schedule(bad_schedules["duplicate_zones"], good_sprinklers)
        pytest.fail("Expected ValueError for duplicate zones")
    except ValueError:
        pass

    try:
        validate_schedule(bad_schedules["invalid_days"], good_sprinklers)
        pytest.fail("Expected ValueError for invalid days")
    except ValueError:
        pass

    try:
        validate_schedule(bad_schedules["duration_too_long"], good_sprinklers)
        pytest.fail("Expected ValueError for duration too long")
    except ValueError:
        pass

    try:
        validate_schedule(bad_schedules["duration_too_short"], good_sprinklers)
        pytest.fail("Expected ValueError for duration too short")
    except ValueError:
        pass

    try:
        validate_schedule(bad_schedules["zone_not_in_sprinklers"], good_sprinklers)
        pytest.fail("Expected ValueError for invalid zone")
    except ValueError:
        pass

def test_schedule_list_validation():
    """Test validation of schedule lists"""
    good_schedule_list = [
        {
            "sched_id": 1,
            "schedule_name": "Default Schedule",
            "schedule_items": [
                {"zone": 1, "day": "M", "duration": 600},
                {"zone": 2, "day": "Tu", "duration": 600},
            ]
        },
        {
            "sched_id": 2,
            "schedule_name": "Summer Schedule",
            "schedule_items": [
                {"zone": 3, "day": "W", "duration": 600},
                {"zone": 4, "day": "Th", "duration": 600},
            ]
        }
    ]

    # Test valid schedule list
    assert validate_schedule_list(good_schedule_list, good_sprinklers) == True

    # Test duplicate schedule IDs
    bad_schedule_list = deepcopy(good_schedule_list)
    bad_schedule_list[1]["sched_id"] = 1
    try:
        validate_schedule_list(bad_schedule_list, good_sprinklers)
        pytest.fail("Expected ValueError for duplicate schedule IDs")
    except ValueError:
        pass

    # Test duplicate schedule names
    bad_schedule_list = deepcopy(good_schedule_list)
    bad_schedule_list[1]["schedule_name"] = "Default Schedule"
    try:
        validate_schedule_list(bad_schedule_list, good_sprinklers)
        pytest.fail("Expected ValueError for duplicate schedule names")
    except ValueError as e:
        assert str(e) == "Validation Error: Duplicate schedule names"

    # Test missing schedule name
    bad_schedule_list = deepcopy(good_schedule_list)
    bad_schedule_list[0]["schedule_name"] = ""
    try:
        validate_schedule_list(bad_schedule_list, good_sprinklers)
        pytest.fail("Expected ValueError for missing schedule name")
    except ValueError:
        pass

    # Test invalid schedule items
    bad_schedule_list = deepcopy(good_schedule_list)
    bad_schedule_list[0]["schedule_items"] = bad_schedules["invalid_days"]
    try:
        validate_schedule_list(bad_schedule_list, good_sprinklers)
        pytest.fail("Expected ValueError for invalid schedule items")
    except ValueError:
        pass

def test_get_scheduled_zones():
    """Test getting scheduled zones for a date"""
    test_schedule = [
        {"zone": 1, "day": "M", "duration": 600},      # Monday, 10 minutes
        {"zone": 2, "day": "ALL", "duration": 900},    # Every day, 15 minutes
        {"zone": 3, "day": "EO", "duration": 1200},    # Odd days, 20 minutes
        {"zone": 4, "day": "NONE", "duration": 1500},  # Never, 25 minutes
        {"zone": 5, "day": "M:W:F", "duration": 600},  # M:W:F, 10 minutes
    ]

    # Test Monday on odd day (01/02/23)
    monday_zones = get_scheduled_zones(test_schedule, "010223")
    assert len(monday_zones) == 3
    assert {"zone": 1, "duration": 600} in monday_zones  # Monday
    assert {"zone": 2, "duration": 900} in monday_zones  # ALL
    assert {"zone": 5, "duration": 600} in monday_zones  # M:W:F

    # Test Tuesday on odd day (01/03/23)
    tuesday_zones = get_scheduled_zones(test_schedule, "010323")
    assert len(tuesday_zones) == 2
    assert {"zone": 2, "duration": 900} in tuesday_zones  # ALL
    assert {"zone": 3, "duration": 1200} in tuesday_zones  # EO

    # Test Wednesday on even day (01/04/23)
    wednesday_zones = get_scheduled_zones(test_schedule, "010423")
    assert len(wednesday_zones) == 2
    assert {"zone": 5, "duration": 600} in wednesday_zones  # M:W:F
    assert {"zone": 2, "duration": 900} in wednesday_zones  # ALL

    # Test invalid date format
    invalid_zones = get_scheduled_zones(test_schedule, "invalid")
    assert len(invalid_zones) == 0
