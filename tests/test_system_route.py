from fastapi.testclient import TestClient

from context import isprinklr

from isprinklr.main import app

client = TestClient(app)

def test_get_status():
  response = client.get("/api/system/status")
  assert response.status_code == 200
  assert response.json() == {"systemStatus": "inactive", "message": None, "active_zone": None, "duration": 0}