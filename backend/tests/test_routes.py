import pytest
import json
from app import app
from services.competitor_service import competitor_service

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Patch competitor_service client to avoid needing DB for simple route tests
    competitor_service.client_restaurant = {'name': 'Test Client', 'address': 'Test Addr'}
    with app.test_client() as client:
        yield client

def test_list_restaurants(client):
    response = client.get('/api/restaurants/list')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'restaurants' in data
    assert isinstance(data['restaurants'], list)

def test_list_platforms(client):
    response = client.get('/api/platforms')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'platforms' in data
    assert 'ubereats' in data['platforms']

def test_get_config(client):
    response = client.get('/api/config')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'platforms' in data
    assert 'cache_ttl' in data
    
def test_update_config(client):
    response = client.post('/api/config', json={'cache_ttl': 7200})
    assert response.status_code == 200
    
    # verify
    response2 = client.get('/api/config')
    data2 = json.loads(response2.data)
    assert data2['cache_ttl'] == 7200

def test_export_unsupported(client):
    response = client.get('/api/export/unknown_report')
    assert response.status_code == 400
