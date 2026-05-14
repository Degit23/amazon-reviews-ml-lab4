import re
import joblib
import configparser
import os
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

# Загружаем конфиг
config = configparser.ConfigParser()
config.read('config.ini')

# Загружаем модель и векторайзер
model = joblib.load('experiments/model.pkl')
vectorizer = joblib.load('experiments/vectorizer.pkl')

# Создаём приложение


# Схема входных данных
class ReviewRequest(BaseModel):
    text: str

# Функция очистки текста
def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Подключение к БД
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT')
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

# Инициализируем БД при старте
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield
app = FastAPI(title="Amazon Reviews Sentiment API", lifespan=lifespan)
# Главный эндпоинт
@app.post('/predict')
def predict(request: ReviewRequest):
    cleaned = clean_text(request.text)
    vec = vectorizer.transform([cleaned])
    pred = model.predict(vec)[0]
    labels = {0: 'negative', 1: 'neutral', 2: 'positive'}
    sentiment = labels[pred]

    # Сохраняем результат в БД
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO predictions (text, sentiment) VALUES (%s, %s)',
        (request.text, sentiment)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        'text': request.text,
        'sentiment': sentiment
    }

# Эндпоинт проверки
@app.get('/health')
def health():
    return {'status': 'ok'}

# Эндпоинт для просмотра последних предсказаний
@app.get('/predictions')
def get_predictions():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT text, sentiment, created_at FROM predictions ORDER BY created_at DESC LIMIT 10')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{'text': r[0], 'sentiment': r[1], 'created_at': str(r[2])} for r in rows]