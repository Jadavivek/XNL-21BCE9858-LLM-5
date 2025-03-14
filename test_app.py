import pytest
from app import app as flask_app
import os

@pytest.fixture
def app():
    # Set test environment
    os.environ['HUGGINGFACE_API_KEY'] = 'dummy_key_for_testing'
    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Enhanced LLM Application" in response.data

def test_history_endpoint(client):
    response = client.get("/api/history")
    assert response.status_code == 200
    assert "history" in response.json