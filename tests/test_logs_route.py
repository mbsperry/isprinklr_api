import os
from fastapi.testclient import TestClient
from unittest.mock import mock_open, patch

from context import isprinklr
from isprinklr.main import app
from isprinklr.paths import logs_path

client = TestClient(app)

SAMPLE_LOGS = """09-11-2024 16:35:31 isprinklr.system DEBUG: Arduino connected
09-12-2024 16:35:52 isprinklr.routers.sprinklers DEBUG: Received: {'zone': 1, 'duration': 1}
09-13-2024 16:35:58 isprinklr.routers.sprinklers ERROR: Failed to stop system: object bool can't be used in 'await' expression
09-14-2024 16:36:04 isprinklr.system ERROR: Failed to stop zone, system is not active
09-15-2024 16:37:12 isprinklr.system INFO: Arduino connected"""

def test_get_logs():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs")
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)
        assert len(logs) == 5  # All sample log lines
        assert "isprinklr.system" in logs[0]

def test_get_logs_with_module_filter():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?module_name=isprinklr.system")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 3  # Only system module logs
        assert all("isprinklr.system" in log for log in logs)

def test_get_logs_with_debug_level():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?debug_level=DEBUG")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2  # Only DEBUG level logs
        assert all("DEBUG" in log for log in logs)

def test_get_logs_with_line_limit():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?lines=2")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 2

def test_get_logs_with_multiple_filters():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?module_name=isprinklr.system&debug_level=ERROR")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1  # Only system ERROR log
        assert "isprinklr.system ERROR" in logs[0]

def test_get_logs_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        response = client.get("/api/logs")
        assert response.status_code == 404
        assert response.json() == {"detail": "Log file not found"}

def test_get_logs_with_invalid_lines():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?lines=-1")
        assert response.status_code == 400 
        assert response.json() == {"detail": "Invalid number of lines"}

def test_get_logs_with_start_date():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?start_date=2024-09-13")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 3  # Only logs from Sept 13 onwards
        assert "09-13-2024" in logs[0]

def test_get_logs_with_date_range():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?start_date=2024-09-12&end_date=2024-09-14")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 3  # Only logs between Sept 12-14
        assert all(date in "".join(logs) for date in ["09-12-2024", "09-13-2024", "09-14-2024"])

def test_get_logs_end_date_without_start():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?end_date=2024-09-14")
        assert response.status_code == 400
        assert response.json() == {"detail": "end_date cannot be used without start_date"}

def test_get_logs_invalid_date_format():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?start_date=2024/09/14")
        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid date format. Use YYYY-MM-DD"}

def test_get_logs_invalid_date_range():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?start_date=2024-09-14&end_date=2024-09-12")
        assert response.status_code == 400
        assert response.json() == {"detail": "start_date cannot be after end_date"}

def test_get_logs_with_date_and_other_filters():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs?start_date=2024-09-13&module_name=isprinklr.system&debug_level=ERROR")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1  # Only system ERROR log after Sept 13
        assert "09-14-2024" in logs[0]
        assert "isprinklr.system ERROR" in logs[0]

def test_get_logs_empty_file():
    with patch("builtins.open", mock_open(read_data="")):
        response = client.get("/api/logs")
        assert response.status_code == 200
        logs = response.json()
        assert isinstance(logs, list)
        assert len(logs) == 0

def test_get_module_list():
    with patch("builtins.open", mock_open(read_data=SAMPLE_LOGS)):
        response = client.get("/api/logs/module_list")
        assert response.status_code == 200
        modules = response.json()
        assert isinstance(modules, list)
        assert sorted(modules) == ["isprinklr.routers.sprinklers", "isprinklr.system"]

def test_get_module_list_empty_file():
    with patch("builtins.open", mock_open(read_data="")):
        response = client.get("/api/logs/module_list")
        assert response.status_code == 200
        modules = response.json()
        assert isinstance(modules, list)
        assert len(modules) == 0

def test_get_module_list_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        response = client.get("/api/logs/module_list")
        assert response.status_code == 404
        assert response.json() == {"detail": "Log file not found"}
