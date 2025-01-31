import pytest
from datetime import datetime
from isprinklr.schedule_util import validate_schedule, validate_schedule_list, get_scheduled_zones

test_sprinklers = [
    {"zone": 1, "name": "Front Lawn"},
    {"zone": 2, "name": "Back Lawn"},
    {"zone": 3, "name": "Garden"},
    {"zone": 4, "name": "Flowers"},
    {"zone": 5, "name": "Side Yard"},
    {"zone": 6, "name": "Patio"},
    {"zone": 7, "name": "Unused"},
    {"zone": 8, "name": "Extra"}
]

def test_validate_schedule_valid():
    schedule = [
        {"zone": 1, "day": "M:W:F", "duration": 300},
        {"zone": 2, "day": "Tu:Th", "duration": 300},
        {"zone": 3, "day": "Sa:Su", "duration": 300}
    ]
    assert validate_schedule(schedule, test_sprinklers) == True

def test_validate_schedule_case_insensitive():
    """Test that day validation is case insensitive."""
    schedule = [
        {"zone": 1, "day": "m:W:f", "duration": 300},      # lowercase
        {"zone": 2, "day": "TU:th", "duration": 300},      # mixed case
        {"zone": 3, "day": "sa:SU", "duration": 300},      # mixed case
        {"zone": 4, "day": "all", "duration": 300},        # lowercase special
        {"zone": 5, "day": "EO", "duration": 300},         # uppercase special
        {"zone": 6, "day": "NoNe", "duration": 300},       # mixed case special
    ]
    assert validate_schedule(schedule, test_sprinklers) == True

def test_validate_schedule_invalid_zone():
    schedule = [
        {"zone": 99, "day": "M:W:F", "duration": 300}
    ]
    with pytest.raises(ValueError, match="Invalid zone"):
        validate_schedule(schedule, test_sprinklers)

def test_validate_schedule_invalid_duration():
    schedule = [
        {"zone": 1, "day": "M:W:F", "duration": -1}
    ]
    with pytest.raises(ValueError, match="Invalid duration"):
        validate_schedule(schedule, test_sprinklers)

def test_validate_schedule_invalid_day():
    schedule = [
        {"zone": 1, "day": "INVALID", "duration": 300}
    ]
    with pytest.raises(ValueError, match="Invalid day"):
        validate_schedule(schedule, test_sprinklers)

def test_validate_schedule_duplicate_zones():
    schedule = [
        {"zone": 1, "day": "M:W:F", "duration": 300},
        {"zone": 1, "day": "Tu:Th", "duration": 300}
    ]
    with pytest.raises(ValueError, match="Duplicate zones"):
        validate_schedule(schedule, test_sprinklers)

def test_validate_schedule_invalid_special_day_combination():
    """Test that special days (ALL, NONE, EO) cannot be combined with other days."""
    invalid_schedules = [
        [{"zone": 1, "day": "ALL:M", "duration": 300}],
        [{"zone": 2, "day": "NONE:Tu", "duration": 300}],
        [{"zone": 3, "day": "EO:W", "duration": 300}],
        [{"zone": 4, "day": "M:ALL", "duration": 300}],
    ]
    for schedule in invalid_schedules:
        with pytest.raises(ValueError, match="Invalid day"):
            validate_schedule(schedule, test_sprinklers)

def test_validate_schedule_list_valid():
    schedules = [
        {
            "schedule_name": "Schedule 1",
            "schedule_items": [
                {"zone": 1, "day": "M:W:F", "duration": 300},
                {"zone": 2, "day": "Tu:Th", "duration": 300}
            ]
        },
        {
            "schedule_name": "Schedule 2",
            "schedule_items": [
                {"zone": 3, "day": "Sa:Su", "duration": 300}
            ]
        }
    ]
    assert validate_schedule_list(schedules, test_sprinklers) == True

def test_validate_schedule_list_duplicate_names():
    schedules = [
        {
            "schedule_name": "Schedule 1",
            "schedule_items": [
                {"zone": 1, "day": "M:W:F", "duration": 300}
            ]
        },
        {
            "schedule_name": "Schedule 1",
            "schedule_items": [
                {"zone": 2, "day": "Tu:Th", "duration": 300}
            ]
        }
    ]
    with pytest.raises(ValueError, match="Duplicate schedule names"):
        validate_schedule_list(schedules, test_sprinklers)

def test_get_scheduled_zones_thursday():
    """Test that all zones scheduled for Thursday are returned."""
    schedule = [
        {"zone": 1, "day": "EO", "duration": 60},      # Even/Odd days
        {"zone": 2, "day": "ALL", "duration": 60},     # Every day
        {"zone": 3, "day": "M:W:F", "duration": 60},   # Not Thursday
        {"zone": 4, "day": "Tu:Th", "duration": 60},   # Includes Thursday
        {"zone": 5, "day": "W:Th:F", "duration": 60},  # Includes Thursday
        {"zone": 6, "day": "Sa:Su", "duration": 60},   # Not Thursday
        {"zone": 7, "day": "NONE", "duration": 60},    # Never
        {"zone": 8, "day": "Su:Th", "duration": 60}    # Includes Thursday
    ]
    
    # Use a Thursday date (December 19, 2024 is a Thursday)
    thursday_zones = get_scheduled_zones(schedule, "121924")
    
    # Should include zones 2 (ALL), 4 (Tu:Th), 5 (W:Th:F), and 8 (Su:Th)
    expected_zones = [
        {"zone": 2, "duration": 60},
        {"zone": 4, "duration": 60},
        {"zone": 5, "duration": 60},
        {"zone": 8, "duration": 60}
    ]
    
    assert sorted(thursday_zones, key=lambda x: x["zone"]) == sorted(expected_zones, key=lambda x: x["zone"])

def test_get_scheduled_zones_case_insensitive():
    """Test that get_scheduled_zones is case insensitive."""
    schedule = [
        {"zone": 1, "day": "all", "duration": 60},     # lowercase ALL
        {"zone": 2, "day": "tu:TH", "duration": 60},   # mixed case days
        {"zone": 3, "day": "NONE", "duration": 60},    # uppercase NONE
        {"zone": 4, "day": "eo", "duration": 60}       # lowercase EO
    ]
    
    # Use a Thursday date (December 19, 2024 is a Thursday)
    thursday_zones = get_scheduled_zones(schedule, "121924")
    
    # Should include zones 1 (all) and 2 (tu:TH)
    expected_zones = [
        {"zone": 1, "duration": 60},
        {"zone": 2, "duration": 60}
    ]
    
    assert sorted(thursday_zones, key=lambda x: x["zone"]) == sorted(expected_zones, key=lambda x: x["zone"])

def test_get_scheduled_zones_even_day():
    """Test that even/odd day scheduling works correctly."""
    schedule = [
        {"zone": 1, "day": "EO", "duration": 60},  # Even/Odd days
        {"zone": 2, "day": "ALL", "duration": 60}  # Every day
    ]
    
    # December 20, 2024 is day 355 of the year (odd)
    odd_day_zones = get_scheduled_zones(schedule, "122024")
    assert {"zone": 1, "duration": 60} in odd_day_zones
    assert {"zone": 2, "duration": 60} in odd_day_zones
    
    # December 19, 2024 is day 354 of the year (even)
    even_day_zones = get_scheduled_zones(schedule, "121924")
    assert {"zone": 1, "duration": 60} not in even_day_zones
    assert {"zone": 2, "duration": 60} in even_day_zones

def test_get_scheduled_zones_invalid_date():
    """Test handling of invalid date format."""
    schedule = [
        {"zone": 1, "day": "ALL", "duration": 60}
    ]
    
    # Invalid date format
    zones = get_scheduled_zones(schedule, "invalid")
    assert zones == []
