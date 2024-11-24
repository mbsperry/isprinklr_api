from fastapi.testclient import TestClient
from typing import List

from context import isprinklr
from isprinklr.schemas import SprinklerCommand, SprinklerConfig
from isprinklr.main import app

client = TestClient(app)

def test_get_sprinklers():
    response = client.get("/api/sprinklers")
    assert response.status_code == 200
    sprinklers: List[SprinklerConfig] = response.json()
    assert isinstance(sprinklers, list)
    assert len(sprinklers) > 0
    # Verify each item matches SprinklerConfig schema
    for sprinkler in sprinklers:
        assert isinstance(sprinkler, dict)
        assert 'zone' in sprinkler
        assert 'name' in sprinkler
        assert isinstance(sprinkler['zone'], int)
        assert isinstance(sprinkler['name'], str)

def test_update_sprinklers_success(mocker):
    new_sprinklers: List[SprinklerConfig] = [
        {"zone": 1, "name": "Updated Front"},
        {"zone": 2, "name": "Updated Back"}
    ]
    mocker.patch('isprinklr.routers.sprinklers.system_status.update_sprinklers', return_value=new_sprinklers)
    response = client.put("/api/sprinklers/", json=new_sprinklers)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Success",
        "zones": new_sprinklers
    }

def test_update_sprinklers_validation_error(mocker):
    invalid_sprinklers: List[SprinklerConfig] = [
        {"zone": 1, "name": "Duplicate Zone"},
        {"zone": 1, "name": "Duplicate Zone"}
    ]
    mocker.patch('isprinklr.routers.sprinklers.system_status.update_sprinklers', 
                side_effect=ValueError("Validation Error: Duplicate zones in sprinklers"))
    response = client.put("/api/sprinklers/", json=invalid_sprinklers)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Failed to update sprinklers, invalid data: Validation Error: Duplicate zones in sprinklers"
    }

def test_update_sprinklers_server_error(mocker):
    sprinklers: List[SprinklerConfig] = [{"zone": 1, "name": "Test"}]
    mocker.patch('isprinklr.routers.sprinklers.system_status.update_sprinklers', 
                side_effect=Exception("Failed to write file"))
    response = client.put("/api/sprinklers/", json=sprinklers)
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to update sprinklers, see logs for details"
    }

def test_start_sprinkler(mocker):
    mocker.patch('isprinklr.routers.sprinklers.system_status.start_sprinkler', return_value=True)
    sprinkler: SprinklerCommand = {"zone": 1, "duration": 300}  # 5 minutes in seconds
    response = client.post("/api/sprinklers/start", json=sprinkler)
    assert response.status_code == 200
    assert response.json() == {"message": "Zone 1 started"}

def test_start_sprinkler_while_running(mocker):
    mocker.patch('isprinklr.routers.sprinklers.system_status.start_sprinkler', 
                side_effect=Exception("Failed to start sprinkler, system already active. Active zone: 2"))
    sprinkler: SprinklerCommand = {"zone": 1, "duration": 60}  # 1 minute in seconds
    response = client.post("/api/sprinklers/start", json=sprinkler)
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to start sprinkler, see logs for details"}

def test_stop_system(mocker):
    mocker.patch('isprinklr.routers.sprinklers.system_status.stop_system', return_value=True)
    response = client.post("/api/sprinklers/stop")
    assert response.status_code == 200
    assert response.json() == {"message": "System stopped"}

def test_stop_system_error(mocker):
    mocker.patch('isprinklr.routers.sprinklers.system_status.stop_system', 
                side_effect=Exception("Failed to stop system"))
    response = client.post("/api/sprinklers/stop")
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to stop system, see logs for details"}
