from fastapi.testclient import TestClient
from app.main import app

def test_project_lifecycle_and_ai_endpoints():
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer mock_vasu_token_xyz"}
        
        # 1. Create Project
        response = client.post("/api/projects/", json={
            "title": "Test Movie",
            "logline": "A test movie logline."
        }, headers=headers)
        assert response.status_code == 201
        project_data = response.json()
        project_id = project_data["id"]
        assert project_data["title"] == "Test Movie"
        
        # 2. Get Project
        response = client.get(f"/api/projects/{project_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Test Movie"
        
        # 3. Generate Story Outline (Gemini mock fallback)
        response = client.post(f"/api/ai/projects/{project_id}/generate-story", json={
            "idea": "An astronaut gets stranded on Mars but discovers a thriving underground coffee shop."
        }, headers=headers)
        assert response.status_code == 200
        res_json = response.json()
        assert "premise" in res_json
        assert "synopsis" in res_json
        assert len(res_json["beat_sheet"]) > 0
        
        # 4. List Projects
        response = client.get("/api/projects/", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) > 0
        
        # 5. Delete Project
        response = client.delete(f"/api/projects/{project_id}", headers=headers)
        assert response.status_code == 204
