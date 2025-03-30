import os
import pytest
from main import app

# Setup a test client using Flask's built-in test client
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# Test 1: Home page loads and contains expected text
def test_homepage_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Upload an Image' in response.data

# Test 2: Uploaded image titles and descriptions are shown
def test_uploaded_images_display(client, monkeypatch):
    # Mock list_files to return a fake image
    monkeypatch.setattr('main.list_files', lambda: ['example.jpg'])

    # Mock GCS blob download to return fake caption data
    class MockBlob:
        def download_as_string(self):
            return b'{"title": "Test Title", "description": "Test Description"}'

    class MockBucket:
        def blob(self, name):
            return MockBlob()

    class MockStorageClient:
        def bucket(self, name):
            return MockBucket()

    monkeypatch.setattr('main.storage.Client', lambda: MockStorageClient())

    # Call home page again
    response = client.get('/')
    assert response.status_code == 200
    assert b'Test Title' in response.data
    assert b'Test Description' in response.data
