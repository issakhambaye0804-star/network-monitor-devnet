#!/usr/bin/env python3
"""
Application de Monitoring Réseau Distribué - Version Développement
Projet d'Examen DEVNET - L3 RI ISI Keur Massar

Version simplifiée utilisant SQLite pour le développement local sans Docker.
"""

import os
import time
import json
import psutil
import socket
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import threading

app = Flask(__name__)

# Configuration de la base de données SQLite pour développement
DATABASE = 'network_monitor_dev.db'

# Configuration du réseau
NODE_ID = os.getenv('NODE_ID', socket.gethostname())
OTHER_NODES = os.getenv('OTHER_NODES', '').split(',') if os.getenv('OTHER_NODES') else []

# Fonctions de base de données SQLite
def init_db():
    """Initialise la base de données SQLite"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Table des statistiques réseau
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS network_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_usage REAL,
            memory_usage REAL,
            network_bytes_sent INTEGER,
            network_bytes_recv INTEGER,
            active_connections INTEGER
        )
    ''')
    
    # Table des statuts de nœuds
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS node_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT UNIQUE NOT NULL,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            ip_address TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Obtient une connexion à la base de données"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Fonctions de monitoring
def get_network_stats():
    """Récupère les statistiques réseau du système"""
    try:
        net_io = psutil.net_io_counters()
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        connections = len(psutil.net_connections())
        
        return {
            'cpu_usage': cpu_percent,
            'memory_usage': memory_percent,
            'network_bytes_sent': net_io.bytes_sent,
            'network_bytes_recv': net_io.bytes_recv,
            'active_connections': connections,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        app.logger.error(f"Erreur lors de la collecte des stats: {e}")
        return None

def save_stats_to_db():
    """Sauvegarde les statistiques dans la base de données"""
    stats = get_network_stats()
    if stats:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Sauvegarder les statistiques réseau
            cursor.execute('''
                INSERT INTO network_stats 
                (node_id, cpu_usage, memory_usage, network_bytes_sent, network_bytes_recv, active_connections)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                NODE_ID,
                stats['cpu_usage'],
                stats['memory_usage'],
                stats['network_bytes_sent'],
                stats['network_bytes_recv'],
                stats['active_connections']
            ))
            
            # Mettre à jour le statut du nœud
            cursor.execute('''
                INSERT OR REPLACE INTO node_status (node_id, last_seen, status, ip_address)
                VALUES (?, CURRENT_TIMESTAMP, 'active', ?)
            ''', (NODE_ID, socket.gethostbyname(socket.gethostname())))
            
            conn.commit()
            conn.close()
            app.logger.info(f"Statistiques sauvegardées pour le nœud {NODE_ID}")
        except Exception as e:
            app.logger.error(f"Erreur lors de la sauvegarde en base: {e}")

def communicate_with_nodes():
    """Communique avec les autres nœuds du réseau"""
    for node_url in OTHER_NODES:
        try:
            import requests
            response = requests.get(f"{node_url}/api/status", timeout=5)
            if response.status_code == 200:
                node_data = response.json()
                # Mettre à jour le statut du nœud distant
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO node_status (node_id, last_seen, status)
                    VALUES (?, CURRENT_TIMESTAMP, 'active')
                ''', (node_url,))
                conn.commit()
                conn.close()
                app.logger.info(f"Communication réussie avec {node_url}")
        except Exception as e:
            app.logger.warning(f"Impossible de contacter {node_url}: {e}")
            # Marquer le nœud comme offline
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO node_status (node_id, last_seen, status)
                VALUES (?, CURRENT_TIMESTAMP, 'offline')
            ''', (node_url,))
            conn.commit()
            conn.close()

def background_monitoring():
    """Tâche de fond pour le monitoring continu"""
    while True:
        save_stats_to_db()
        communicate_with_nodes()
        time.sleep(30)  # Monitoring toutes les 30 secondes

# Routes de l'application
@app.route('/')
def index():
    """Page principale avec dashboard"""
    return render_template('index.html', node_id=NODE_ID)

@app.route('/api/stats')
def get_stats():
    """API pour récupérer les statistiques actuelles"""
    stats = get_network_stats()
    if stats:
        stats['node_id'] = NODE_ID
        return jsonify(stats)
    return jsonify({'error': 'Impossible de récupérer les statistiques'}), 500

@app.route('/api/status')
def get_status():
    """API pour récupérer le statut du nœud"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM node_status WHERE node_id = ?', (NODE_ID,))
        node_status = cursor.fetchone()
        conn.close()
        
        if node_status:
            return jsonify(dict(node_status))
        else:
            # Créer le statut s'il n'existe pas
            save_stats_to_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM node_status WHERE node_id = ?', (NODE_ID,))
            node_status = cursor.fetchone()
            conn.close()
            return jsonify(dict(node_status))
    except Exception as e:
        app.logger.error(f"Erreur get_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """API pour récupérer l'historique des statistiques"""
    try:
        limit = request.args.get('limit', 50, type=int)
        node_id = request.args.get('node_id', NODE_ID)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM network_stats 
            WHERE node_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (node_id, limit))
        
        stats = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(stat) for stat in stats])
    except Exception as e:
        app.logger.error(f"Erreur get_history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes')
def get_nodes():
    """API pour récupérer la liste des nœuds"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM node_status')
        nodes = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(node) for node in nodes])
    except Exception as e:
        app.logger.error(f"Erreur get_nodes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/network-test')
def network_test():
    """Test de connectivité réseau"""
    try:
        # Test de connexion à la base de données
        db_status = "OK"
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
        except Exception:
            db_status = "ERROR"
        
        # Test de connectivité avec les autres nœuds
        nodes_status = {}
        for node_url in OTHER_NODES:
            try:
                import requests
                response = requests.get(f"{node_url}/api/status", timeout=3)
                nodes_status[node_url] = "OK" if response.status_code == 200 else "ERROR"
            except Exception:
                nodes_status[node_url] = "ERROR"
        
        return jsonify({
            'node_id': NODE_ID,
            'database': db_status,
            'nodes': nodes_status,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check"""
    return jsonify({'status': 'healthy', 'node_id': NODE_ID})

# Initialisation de l'application
def initialize():
    """Initialisation de la base de données et démarrage du monitoring"""
    try:
        init_db()
        app.logger.info("Base de données initialisée")
        
        # Démarrage de la tâche de fond
        monitor_thread = threading.Thread(target=background_monitoring, daemon=True)
        monitor_thread.start()
        app.logger.info("Monitoring démarré")
        
    except Exception as e:
        app.logger.error(f"Erreur lors de l'initialisation: {e}")

if __name__ == '__main__':
    # Initialisation pour le développement
    init_db()
    initialize()
    
    # Démarrage de l'application
    print("🌐 Démarrage de Network Monitor (Mode Développement)")
    print(f"📊 Node ID: {NODE_ID}")
    print(f"🌐 Accès: http://localhost:5000")
    print(f"🔧 Mode: SQLite (Développement)")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
