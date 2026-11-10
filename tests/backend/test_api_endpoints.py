import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Renewable Energy Intelligence Platform" in data["platform"]

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_plants_api(client):
    response = client.get("/api/plants")
    assert response.status_code == 200
    plants = response.json()
    assert len(plants) >= 5

def test_analytics_overview_api(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_renewable_energy_mwh" in data

def test_anomalies_api(client):
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    anomalies = response.json()
    assert isinstance(anomalies, list)
    assert len(anomalies) >= 1
    assert {"id", "status", "severity", "energy_source"} <= anomalies[0].keys()

    sample = anomalies[0]
    filtered = client.get(
        "/api/anomalies",
        params={
            "status": sample["status"].upper(),
            "severity": sample["severity"].upper(),
            "energy_source": sample["energy_source"].upper(),
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()
    assert all(
        anomaly["status"].lower() == sample["status"].lower()
        and anomaly["severity"].lower() == sample["severity"].lower()
        and anomaly["energy_source"].lower() == sample["energy_source"].lower()
        for anomaly in filtered.json()
    )

def test_anomaly_status_rejects_invalid_and_missing_ids(client):
    invalid = client.patch(
        "/api/anomalies/nonexistent/status",
        json={"status": "not-a-status"},
    )
    assert invalid.status_code == 400

    missing = client.patch(
        "/api/anomalies/nonexistent/status",
        json={"status": "Ignored"},
    )
    assert missing.status_code == 404

def test_spark_jobs_api(client):
    response = client.get("/api/spark/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)

def test_reports_overview(client):
    response = client.get("/api/reports/overview")
    assert response.status_code == 200
    reports = response.json()
    assert len(reports) >= 8
