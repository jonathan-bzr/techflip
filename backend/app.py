from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app) # Permet au frontend de communiquer avec le backend

DB_NAME = "database.db"

def init_db():
    """ Initialise la base de données SQLite """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            buy_price REAL NOT NULL,
            repair_cost REAL DEFAULT 0,
            target_price REAL NOT NULL,
            status TEXT CHECK(status IN ('En réparation', 'En vente', 'Vendu')) NOT NULL DEFAULT 'En réparation',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# API Endpoints

@app.route('/api/pcs', methods=['GET'])
def get_pcs():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pcs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    pcs = [dict(row) for row in rows]
    return jsonify(pcs)

@app.route('/api/pcs', methods=['POST'])
def add_pc():
    data = request.json
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pcs (name, buy_price, repair_cost, target_price, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['name'], data['buy_price'], data.get('repair_cost', 0), data['target_price'], data.get('status', 'En réparation')))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "PC ajouté avec succès"}), 201

@app.route('/api/pcs/<int:pc_id>/status', methods=['PUT'])
def update_status(pc_id):
    data = request.json
    new_status = data.get('status')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE pcs SET status = ? WHERE id = ?", (new_status, pc_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Statut mis à jour"})

@app.route('/api/pcs/<int:pc_id>', methods=['DELETE'])
def delete_pc(pc_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pcs WHERE id = ?", (pc_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "PC supprimé"})

if __name__ == '__main__':
    init_db()
    print("[*] Base de données SQLite prête.")
    app.run(host='0.0.0.0', port=5000, debug=True)