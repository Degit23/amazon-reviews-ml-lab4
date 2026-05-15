import os
import json
import time
import psycopg2
import hvac
from kafka import KafkaConsumer

def get_secrets():
    client = hvac.Client(
        url=os.getenv('VAULT_ADDR', 'http://vault:8200'),
        token=os.getenv('VAULT_TOKEN', 'root-token')
    )
    secret = client.secrets.kv.read_secret_version(path='postgres')
    return secret['data']['data']

def get_db_connection():
    secrets = get_secrets()
    return psycopg2.connect(
        dbname=secrets['db'],
        user=secrets['user'],
        password=secrets['password'],
        host=secrets['host'],
        port=secrets['port']
    )

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

def main():
    print("Consumer starting...")
    time.sleep(15)

    init_db()
    print("DB initialized!")

    consumer = KafkaConsumer(
        'predictions',
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id='predictions-group'
    )

    print("Listening for messages...")
    for message in consumer:
        data = message.value
        print(f"Received: {data}")

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO predictions (text, sentiment) VALUES (%s, %s)',
            (data['text'], data['sentiment'])
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Saved to DB: {data}")

if __name__ == '__main__':
    main()