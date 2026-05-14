import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

@patch('src.app.get_db_connection')
def test_predict_positive(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    response = client.post('/predict', json={'text': 'This album is absolutely amazing!'})
    assert response.status_code == 200
    assert response.json()['sentiment'] == 'positive'

@patch('src.app.get_db_connection')
def test_predict_negative(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    response = client.post('/predict', json={'text': 'Terrible quality, waste of money.'})
    assert response.status_code == 200
    assert response.json()['sentiment'] == 'negative'

@patch('src.app.get_db_connection')
def test_predict_empty(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    response = client.post('/predict', json={'text': ''})
    assert response.status_code == 200
    assert 'sentiment' in response.json()

@patch('src.app.get_db_connection')
def test_predict_returns_text(mock_db):
    mock_conn = MagicMock()
    mock_db.return_value = mock_conn
    text = 'Great music!'
    response = client.post('/predict', json={'text': text})
    assert response.json()['text'] == text

@patch('src.app.get_db_connection')
def test_predictions_endpoint(mock_db):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = [
        ('Great album!', 'positive', '2026-05-14 12:00:00')
    ]
    mock_db.return_value = mock_conn
    response = client.get('/predictions')
    assert response.status_code == 200

## sssda