import re
import joblib
import configparser
import os
import psycopg2
import hvac
from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Загружаем конфиг
config = configparser.ConfigParser()
config.read('config.ini')

# Загружаем модель и векторайзер
model = joblib.load('experiments/model.pkl')
vectorizer = joblib.load('experiments/vectorizer.pkl')

# Получаем секреты из Vault
def get_secrets():
    client = hvac.Client(
        url=os.getenv('VAULT_ADDR', 'http://vault:8200'),
        token=os.getenv('VAULT_TOKEN', 'root-token')
    )
    secret = client.secrets.kv.read_secret_version(path='postgres')
    return secret['data']['data']

# Подключение к БД через секреты из Vault
def get_db_connection():
    secrets = get_secrets()
    return psycopg2.connect(
        dbname=secrets['db'],
        user=secrets['user'],
        password=secrets['password'],
        host=secrets['host'],
        port=secrets['port']
    )

# Создаём таблицу если не существует
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            sentiment VARCHAR(10) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="Amazon Reviews Sentiment API", lifespan=lifespan)

class ReviewRequest(BaseModel):
    text: str

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

@app.post('/predict')
def predict(request: ReviewRequest):
    cleaned = clean_text(request.text)
    vec = vectorizer.transform([cleaned])
    pred = model.predict(vec)[0]
    labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
    sentiment = labels[pred]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO predictions (text, sentiment) VALUES (%s, %s)',
        (request.text, sentiment)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {'text': request.text, 'sentiment': sentiment}

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/predictions')
def get_predictions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT text, sentiment, created_at FROM predictions ORDER BY created_at DESC LIMIT 10')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'text': r[0], 'sentiment': r[1], 'created_at': str(r[2])} for r in rows]