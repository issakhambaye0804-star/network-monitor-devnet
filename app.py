#!/usr/bin/env python3
"""
Application de Monitoring Réseau Distribué
Projet d'Examen DEVNET - L3 RI ISI Keur Massar

Cette application Flask permet de monitorer un réseau distribué
avec communication entre conteneurs et base de données PostgreSQL.
"""

import os
import time
import json
import psutil
import socket
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import threading

app = Flask(__name__)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://network_user:network_pass@db:5432/network_monitor'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuration du réseau
NODE_ID = os.getenv('NODE_ID', socket.gethostname())
OTHER_NODES = os.getenv('OTHER_NODES', '').split(',') if os.getenv('OTHER_NODES') else []

# Modèles de base de données
class NetworkStats(db.Model):
    __tablename__ = 'network_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_usage = db.Column(db.Float)
    memory_usage = db.Column(db.Float)
    network_bytes_sent = db.Column(db.BigInteger)
    network_bytes_recv = db.Column(db.BigInteger)
    active_connections = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_recv': self.network_bytes_recv,
            'active_connections': self.active_connections
        }

class NodeStatus(db.Model):
    __tablename__ = 'node_status'
    
    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.String(100), nullable=False, unique=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    ip_address = db.Column(db.String(45))
    
    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'last_seen': self.last_seen.isoformat(),
            'status': self.status,
            'ip_address': self.ip_address
        }

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
            # Sauvegarder les statistiques réseau
            network_stat = NetworkStats(
                node_id=NODE_ID,
                cpu_usage=stats['cpu_usage'],
                memory_usage=stats['memory_usage'],
                network_bytes_sent=stats['network_bytes_sent'],
                network_bytes_recv=stats['network_bytes_recv'],
                active_connections=stats['active_connections']
            )
            db.session.add(network_stat)
            
            # Mettre à jour le statut du nœud
            node_status = NodeStatus.query.filter_by(node_id=NODE_ID).first()
            if not node_status:
                node_status = NodeStatus(
                    node_id=NODE_ID,
                    ip_address=socket.gethostbyname(socket.gethostname())
                )
                db.session.add(node_status)
            else:
                node_status.last_seen = datetime.utcnow()
                node_status.status = 'active'
            
            db.session.commit()
            app.logger.info(f"Statistiques sauvegardées pour le nœud {NODE_ID}")
        except Exception as e:
            app.logger.error(f"Erreur lors de la sauvegarde en base: {e}")
            db.session.rollback()

def communicate_with_nodes():
    """Communique avec les autres nœuds du réseau"""
    for node_url in OTHER_NODES:
        try:
            response = requests.get(f"{node_url}/api/status", timeout=5)
            if response.status_code == 200:
                node_data = response.json()
                # Mettre à jour le statut du nœud distant
                node_status = NodeStatus.query.filter_by(node_id=node_data.get('node_id')).first()
                if node_status:
                    node_status.last_seen = datetime.utcnow()
                    node_status.status = 'active'
                    db.session.commit()
                    app.logger.info(f"Communication réussie avec {node_url}")
        except Exception as e:
            app.logger.warning(f"Impossible de contacter {node_url}: {e}")
            # Marquer le nœud comme offline
            node_status = NodeStatus.query.filter_by(node_id=node_url).first()
            if node_status:
                node_status.status = 'offline'
                db.session.commit()

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
        node_status = NodeStatus.query.filter_by(node_id=NODE_ID).first()
        if node_status:
            return jsonify(node_status.to_dict())
        else:
            # Créer le statut s'il n'existe pas
            new_status = NodeStatus(
                node_id=NODE_ID,
                ip_address=socket.gethostbyname(socket.gethostname())
            )
            db.session.add(new_status)
            db.session.commit()
            return jsonify(new_status.to_dict())
    except Exception as e:
        app.logger.error(f"Erreur get_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def get_history():
    """API pour récupérer l'historique des statistiques"""
    try:
        limit = request.args.get('limit', 50, type=int)
        node_id = request.args.get('node_id', NODE_ID)
        
        stats = NetworkStats.query.filter_by(node_id=node_id)\
                .order_by(NetworkStats.timestamp.desc())\
                .limit(limit)\
                .all()
        
        return jsonify([stat.to_dict() for stat in stats])
    except Exception as e:
        app.logger.error(f"Erreur get_history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/nodes')
def get_nodes():
    """API pour récupérer la liste des nœuds"""
    try:
        nodes = NodeStatus.query.all()
        return jsonify([node.to_dict() for node in nodes])
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
            db.session.execute(text('SELECT 1'))
        except Exception:
            db_status = "ERROR"
        
        # Test de connectivité avec les autres nœuds
        nodes_status = {}
        for node_url in OTHER_NODES:
            try:
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
    """Health check pour Docker"""
    return jsonify({'status': 'healthy', 'node_id': NODE_ID})

# Initialisation de l'application
@app.before_first_request
def initialize():
    """Initialisation de la base de données et démarrage du monitoring"""
    try:
        # Création des tables
        db.create_all()
        app.logger.info("Base de données initialisée")
        
        # Démarrage de la tâche de fond
        monitor_thread = threading.Thread(target=background_monitoring, daemon=True)
        monitor_thread.start()
        app.logger.info("Monitoring démarré")
        
    except Exception as e:
        app.logger.error(f"Erreur lors de l'initialisation: {e}")

if __name__ == '__main__':
    # Mode développement
    with app.app_context():
        db.create_all()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
