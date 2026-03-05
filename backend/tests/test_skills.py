def test_list_skills_empty(client):
    resp = client.get("/api/v1/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["data"] == []


def test_create_and_get_skill(client):
    # Create
    resp = client.post(
        "/api/v1/skills",
        json={
            "name": "Test Skill",
            "description": "A test skill",
            "content": "# Test\nHello world",
            "category_id": 1,
            "tag_names": ["python", "testing"],
        },
    )
    assert resp.status_code == 201
    skill = resp.json()
    assert skill["name"] == "Test Skill"
    assert skill["slug"] == "test-skill"
    assert len(skill["tags"]) == 2

    # Get by slug
    resp = client.get("/api/v1/skills/test-skill")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Skill"

    # List
    resp = client.get("/api/v1/skills")
    assert resp.json()["total"] == 1


def test_update_skill(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Update Me",
            "description": "Before update",
            "content": "# Before",
            "category_id": 1,
        },
    )
    resp = client.put(
        "/api/v1/skills/update-me",
        json={"description": "After update"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "After update"


def test_delete_skill(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Delete Me",
            "description": "Will be deleted",
            "content": "# Gone",
            "category_id": 1,
        },
    )
    resp = client.delete("/api/v1/skills/delete-me")
    assert resp.status_code == 204

    resp = client.get("/api/v1/skills/delete-me")
    assert resp.status_code == 404


def test_download_skill(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Download Test",
            "description": "Downloadable",
            "content": "# SKILL.md content here",
            "category_id": 1,
        },
    )
    resp = client.get("/api/v1/skills/download-test/download")
    assert resp.status_code == 200
    assert "SKILL.md content here" in resp.text


def test_install_count(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Install Test",
            "description": "Countable",
            "content": "# Count",
            "category_id": 1,
        },
    )
    resp = client.post("/api/v1/skills/install-test/install")
    assert resp.status_code == 200
    assert resp.json()["install_count"] == 1

    resp = client.post("/api/v1/skills/install-test/install")
    assert resp.json()["install_count"] == 2


def test_list_categories(client):
    resp = client.get("/api/v1/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) >= 1
    assert cats[0]["slug"] == "development"


def test_get_category_with_count(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Cat Count Skill",
            "description": "For counting",
            "content": "# Count",
            "category_id": 1,
        },
    )
    resp = client.get("/api/v1/categories/development")
    assert resp.status_code == 200
    assert resp.json()["skill_count"] == 1


def test_duplicate_skill_name(client):
    client.post(
        "/api/v1/skills",
        json={
            "name": "Unique Skill",
            "description": "First",
            "content": "# First",
            "category_id": 1,
        },
    )
    resp = client.post(
        "/api/v1/skills",
        json={
            "name": "Unique Skill",
            "description": "Second",
            "content": "# Second",
            "category_id": 1,
        },
    )
    assert resp.status_code == 409
