from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.api import datasets as datasets_api
from backend.app.core.config import settings
from backend.app.core.security import require_supabase_user
from backend.app.main import app


def test_upload_endpoints_are_authenticated_and_owner_scoped(tmp_path, monkeypatch):
    owner = SimpleNamespace(id="11111111-1111-4111-8111-111111111111")
    other_owner = SimpleNamespace(id="22222222-2222-4222-8222-222222222222")
    current_owner = {"user": owner}
    monkeypatch.setattr(settings, "SUPABASE_NORMALIZED_SCHEMA_ENABLED", False)
    monkeypatch.setattr(datasets_api, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(datasets_api, "_schedule_processing", lambda *_args: None)
    app.dependency_overrides[require_supabase_user] = lambda: current_owner["user"]

    content = (
        b"timestamp,power_kw\n"
        b"2025-01-01T00:00:00Z,10\n"
        b"2025-01-01T01:00:00Z,12\n"
    )
    dataset_id = None
    with TestClient(app) as client:
        try:
            response = client.post(
                "/api/datasets/upload",
                data={"energy_source": "solar"},
                files={"file": ("telemetry.csv", content, "text/csv")},
            )
            assert response.status_code == 202
            dataset_id = response.json()["dataset"]["id"]
            assert response.json()["dataset"]["processing_status"] == "queued"
            assert "storage_location" not in response.json()["dataset"]
            assert "sha256" not in response.json()["dataset"]

            assert client.get("/api/datasets").json()["datasets"][0]["id"] == dataset_id
            assert client.get(f"/api/datasets/{dataset_id}").status_code == 200
            datasets_api.dataset_repository.insert_records(dataset_id, [{
                "row_number": 1,
                "classification": "valid",
                "issues": [],
                "record": {"timestamp": "2025-01-01T00:00:00Z", "power_kw": 10},
            }])
            preview = client.get(f"/api/datasets/{dataset_id}/preview").json()
            assert preview["total"] == 1
            assert preview["records"][0]["record"]["power_kw"] == 10

            duplicate = client.post(
                "/api/datasets/upload",
                data={"energy_source": "solar"},
                files={"file": ("copy.csv", content, "text/csv")},
            )
            assert duplicate.status_code == 409

            current_owner["user"] = other_owner
            assert client.get(f"/api/datasets/{dataset_id}").status_code == 404
            current_owner["user"] = owner

            cancelled = client.post(f"/api/datasets/{dataset_id}/cancel")
            assert cancelled.status_code == 202
            assert client.get(f"/api/datasets/{dataset_id}/status").json()["processing_status"] == "cancelled"

            delete_response = client.delete(f"/api/datasets/{dataset_id}")
            assert delete_response.status_code == 204
            assert not (tmp_path / f"{dataset_id}.csv").exists()
            dataset_id = None
        finally:
            if dataset_id:
                stored = datasets_api.dataset_repository.delete(dataset_id, owner.id)
                if stored:
                    (tmp_path / f"{dataset_id}.csv").unlink(missing_ok=True)
            app.dependency_overrides.pop(require_supabase_user, None)
