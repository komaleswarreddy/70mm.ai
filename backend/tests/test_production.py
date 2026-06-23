from fastapi.testclient import TestClient
from app.main import app

def test_production_and_planning_endpoints():
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer mock_vasu_token_xyz"}

        # 1. Create a project
        response = client.post("/api/projects/", json={
            "title": "Production Test Movie",
            "logline": "A test movie logline."
        }, headers=headers)
        assert response.status_code == 201
        project_data = response.json()
        project_id = project_data["id"]

        # Populate a Scene for testing
        response = client.get(f"/api/projects/{project_id}", headers=headers)
        # Verify initial state contains scenes array (even if empty)
        assert "scenes" in response.json()

        # 2. Test Call Sheets CRUD
        response = client.post(f"/api/projects/{project_id}/callsheets", json={
            "date": "2026-10-15",
            "call_time": "07:00 AM",
            "location": "Metro soundstage 4",
            "notes": "Bring umbrellas"
        }, headers=headers)
        assert response.status_code == 201
        cs_data = response.json()
        cs_id = cs_data["id"]
        assert cs_data["date"] == "2026-10-15"

        response = client.get(f"/api/projects/{project_id}/callsheets", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

        # Delete call sheet
        response = client.delete(f"/api/callsheets/{cs_id}", headers=headers)
        assert response.status_code == 204

        # 3. Test Budget CRUD
        response = client.post(f"/api/projects/{project_id}/budget", json={
            "category": "Equipment",
            "name": "Arri Alexa Camera rental",
            "cost": 1500
        }, headers=headers)
        assert response.status_code == 201
        item_data = response.json()
        item_id = item_data["id"]
        assert item_data["cost"] == 1500

        response = client.get(f"/api/projects/{project_id}/budget", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

        # Delete item
        response = client.delete(f"/api/budget/{item_id}", headers=headers)
        assert response.status_code == 204

        # 4. Test Comments CRUD
        response = client.post(f"/api/projects/{project_id}/comments", json={
            "user_name": "Sarah",
            "role": "Writer",
            "content": "Make the opening sequence more high-contrast."
        }, headers=headers)
        assert response.status_code == 201
        c_data = response.json()
        c_id = c_data["id"]

        response = client.get(f"/api/projects/{project_id}/comments", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

        # Delete comment
        response = client.delete(f"/api/comments/{c_id}", headers=headers)
        assert response.status_code == 204

        # 5. Test Version Snapshots
        response = client.post(f"/api/projects/{project_id}/versions", json={
            "version_name": "Draft 1.0"
        }, headers=headers)
        assert response.status_code == 201
        v_data = response.json()
        v_id = v_data["id"]
        assert v_data["version_name"] == "Draft 1.0"

        response = client.get(f"/api/projects/{project_id}/versions", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

        # Restore snapshot
        response = client.post(f"/api/versions/{v_id}/restore", headers=headers)
        assert response.status_code == 200

        # 6. Test Cinematic RAG Search
        response = client.post("/api/rag/query", data={"query": "Save the Cat Catalyst beat"}, headers=headers)
        assert response.status_code == 200
        rag_data = response.json()
        assert "results" in rag_data
        assert len(rag_data["results"]) > 0

        # Clean up project
        client.delete(f"/api/projects/{project_id}", headers=headers)
