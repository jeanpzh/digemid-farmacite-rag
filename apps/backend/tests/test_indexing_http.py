from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.indexing import get_indexing_service
from app.routers.indexing import router


class FakeIndexingService:
    def __init__(self):
        self.run_id = uuid4()
        self.calls = []

    def start(self, collection, mode):
        self.calls.append(("start", collection, mode))
        return {
            "run_id": self.run_id,
            "collection": collection,
            "mode": mode,
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "completed": 0,
            "total": 2,
            "progress": 0,
            "documents": [],
        }

    def get_status(self, run_id):
        self.calls.append(("status", run_id))
        return {
            "run_id": run_id,
            "collection": "digemid",
            "mode": "pending",
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "completed": 1,
            "total": 2,
            "progress": 50,
            "documents": [],
        }

    def pause(self, run_id):
        self.calls.append(("pause", run_id))
        return self.get_status(run_id) | {"status": "paused"}

    def resume(self, run_id):
        self.calls.append(("resume", run_id))
        return self.get_status(run_id)

    def cancel(self, run_id):
        self.calls.append(("cancel", run_id))
        return self.get_status(run_id) | {"status": "cancelled"}


def create_client(service):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_indexing_service] = lambda: service
    return TestClient(app)


def test_start_indexing_run_returns_a_pollable_run():
    service = FakeIndexingService()

    with create_client(service) as client:
        response = client.post(
            "/api/v1/indexing/runs",
            json={"collection": "digemid", "mode": "pending"},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert response.json()["total"] == 2
    assert service.calls[0] == ("start", "digemid", "pending")


def test_indexing_run_status_and_controls_are_exposed():
    service = FakeIndexingService()

    with create_client(service) as client:
        run_id = str(service.run_id)
        status = client.get(f"/api/v1/indexing/runs/{run_id}")
        paused = client.post(f"/api/v1/indexing/runs/{run_id}/pause")
        resumed = client.post(f"/api/v1/indexing/runs/{run_id}/resume")
        cancelled = client.post(f"/api/v1/indexing/runs/{run_id}/cancel")

    assert status.status_code == 200
    assert status.json()["progress"] == 50
    assert paused.json()["status"] == "paused"
    assert resumed.json()["status"] == "running"
    assert cancelled.json()["status"] == "cancelled"
