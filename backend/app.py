import os
import time
import random
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from curl_cffi import requests as curl_requests

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Récupération de l'URL PostgreSQL depuis la variable d'environnement (ou fallback local)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/techflip")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "TON_WEBHOOK_DISCORD")

# --- BASE DE DONNÉES POSTGRESQL ---
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pcs (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            buy_price NUMERIC NOT NULL,
            repair_cost NUMERIC DEFAULT 0,
            target_price NUMERIC NOT NULL,
            status VARCHAR(50) DEFAULT 'En réparation',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# --- BOT VINTED EN BACKGROUND THREAD ---
def run_vinted_bot():
    print("[*] Lancement du Bot Vinted intégré en arrière-plan...")
    seen_ids = set()
    queries = ["pc portable hs", "pc portable lent", "tour pc hs"]
    
    while True:
        try:
            session = curl_requests.Session(impersonate="chrome120")
            session.get("https://www.vinted.fr", timeout=10)
            
            for q in queries:
                url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={q}&price_to=100&order=newest_first&per_page=5"
                res = session.get(url, impersonate="chrome120", timeout=10)
                if res.status_code == 200:
                    items = res.json().get('items', [])
                    for item in reversed(items):
                        item_id = item.get('id')
                        if item_id not in seen_ids:
                            seen_ids.add(item_id)
                            # Alerte Discord
                            payload = {"embeds": [{"title": f"💻 {item.get('title')}", "url": item.get('url'), "description": f"Prix: {item.get('price')}€"}]}
                            curl_requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
                time.sleep(random.randint(5, 10))
        except Exception as e:
            print(f"[-] Erreur Bot Vinted: {e}")
            
        time.sleep(60) # Pause de 1 minute entre deux scans

# --- ROUTES API ---
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pcs ORDER BY id DESC")
    pcs = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(pcs)

@app.route('/api/pcs', methods=['POST'])
def add_pc():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pcs (name, buy_price, repair_cost, target_price, status)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    ''', (data['name'], data['buy_price'], data.get('repair_cost', 0), data['target_price'], data.get('status', 'En réparation')))
    new_id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"id": new_id}), 201

# --- DÉMARRAGE ---
init_db()

# Démarrage du bot dans un thread séparé pour ne pas bloquer Flask
bot_thread = threading.Thread(target=run_vinted_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)