# 🌐 Network Monitor Distribué

**Projet d'Examen DEVNET - L3 RI ISI Keur Massar**

Application Flask de monitoring réseau distribué avec communication entre conteneurs Docker et base de données PostgreSQL.

## 📋 Description du Projet

Ce projet répond aux exigences de l'examen DEVNET en créant une application web qui:

- **Monitorise un réseau distribué** en temps réel
- **Communique entre plusieurs conteneurs** Docker
- **Utilise une base de données PostgreSQL** conteneurisée
- **Démontre les concepts réseau** (communication API, monitoring, échange de données)
- **Est entièrement conteneurisée** avec Docker

## 🏗️ Architecture du Système

```
┌─────────────────┐    ┌─────────────────┐
│   App Flask 1   │    │   App Flask 2   │
│   (Port 5001)   │    │   (Port 5002)   │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌─────────────────┐
          │  Nginx (Port 80)│
          │   Load Balancer │
          └─────────┬───────┘
                    │
          ┌─────────────────┐
          │   PostgreSQL    │
          │   (Port 5432)   │
          └─────────────────┘
```

## 🚀 Fonctionnalités

### Monitoring Système
- **CPU Usage**: Surveillance de l'utilisation du processeur
- **Memory Usage**: Monitoring de la mémoire RAM
- **Network Traffic**: Analyse du trafic réseau (bytes envoyés/reçus)
- **Active Connections**: Nombre de connexions réseau actives

### Fonctionnalités Réseau
- **Communication Inter-Conteneurs**: Les instances Flask communiquent entre elles
- **Health Checks**: Vérification de la connectivité réseau
- **Node Status**: Statut en temps réel de tous les nœuds du réseau
- **API REST**: Endpoints pour l'échange de données

### Interface Web
- **Dashboard Moderne**: Interface responsive avec TailwindCSS
- **Graphiques Temps Réel**: Visualisation avec Chart.js
- **Mises à Jour Automatiques**: Rafraîchissement toutes les 5 secondes
- **Test de Connectivité**: Bouton pour tester le réseau

## 🛠️ Technologies Utilisées

| Technologie | Rôle |
|-------------|------|
| **Flask** | Framework web principal |
| **PostgreSQL** | Base de données pour les statistiques |
| **Docker** | Conteneurisation de l'application |
| **Docker Compose** | Orchestration des services |
| **Nginx** | Load balancing et reverse proxy |
| **psutil** | Monitoring des ressources système |
| **Chart.js** | Graphiques en temps réel |
| **TailwindCSS** | Styling moderne |

## 📦 Installation

### Prérequis
- Docker et Docker Compose installés
- Git (pour cloner le repository)

### Étapes d'Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd network-monitor
```

2. **Construire et démarrer les services**
```bash
docker-compose up --build -d
```

3. **Vérifier l'installation**
```bash
# Vérifier les conteneurs
docker-compose ps

# Voir les logs
docker-compose logs -f
```

### Accès à l'Application

- **Dashboard Principal**: http://localhost
- **Instance 1**: http://localhost:5001
- **Instance 2**: http://localhost:5002
- **Base de données**: localhost:5432

## 🔧 Configuration

### Variables d'Environnement

Les variables suivantes peuvent être configurées dans `docker-compose.yml`:

```yaml
environment:
  DATABASE_URL: postgresql://network_user:network_pass@db:5432/network_monitor
  NODE_ID: node-1
  OTHER_NODES: http://app2:5000
```

### Personnalisation

- **Nombre d'instances**: Ajoutez plus de services `app3`, `app4`, etc.
- **Base de données**: Modifiez `POSTGRES_*` variables
- **Réseau**: Changez le subnet dans `networks.network_monitor_net`

## 📡 API Endpoints

### Monitoring
- `GET /api/stats` - Statistiques actuelles du nœud
- `GET /api/history` - Historique des statistiques
- `GET /api/nodes` - Liste des nœuds du réseau
- `GET /api/status` - Statut du nœud actuel

### Réseau
- `GET /api/network-test` - Test de connectivité réseau
- `GET /health` - Health check pour Docker

## 🔄 Déploiement Distribué

### Sur Plusieurs Machines

1. **Machine 1 (Master)**
```bash
docker-compose up -d db app1 nginx
```

2. **Machine 2 (Worker)**
```bash
# Modifier OTHER_NODES pour pointer vers machine 1
export OTHER_NODES=http://<machine1-ip>:5001
docker-compose up -d app2
```

### Docker Hub (Optionnel)

1. **Construire l'image**
```bash
docker build -t <username>/network-monitor .
```

2. **Push vers Docker Hub**
```bash
docker push <username>/network-monitor
```

3. **Utiliser dans docker-compose.yml**
```yaml
services:
  app1:
    image: <username>/network-monitor:latest
```

## 🧪 Tests

### Test de Connectivité
```bash
# Test depuis l'hôte
curl http://localhost/api/network-test

# Test entre conteneurs
docker exec network_monitor_app1 curl http://app2:5000/api/status
```

### Test de la Base de Données
```bash
docker exec -it network_monitor_db psql -U network_user -d network_monitor -c "SELECT * FROM node_status;"
```

## 📊 Monitoring en Production

### Logs
```bash
# Logs de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f app1
```

### Statistiques
```bash
# Utilisation des ressources
docker stats

# Espace disque utilisé
docker system df
```

## 🔒 Sécurité

- **Utilisateur non-root**: L'application s'exécute avec `appuser`
- **Variables d'environnement**: Pas de mots de passe en dur
- **Health checks**: Surveillance de l'état des services
- **Réseau isolé**: Sous-réseau Docker dédié

## 🐛 Dépannage

### Problèmes Communs

1. **Port déjà utilisé**
```bash
# Vérifier les ports
netstat -tulpn | grep :5000
# Changer les ports dans docker-compose.yml
```

2. **Connexion base de données refusée**
```bash
# Vérifier que la base est prête
docker-compose logs db
# Attendre que le service soit healthy
docker-compose ps
```

3. **Communication inter-conteneurs échoue**
```bash
# Vérifier le réseau Docker
docker network ls
docker network inspect network_monitor_network_monitor_net
```

### Nettoyage Complet
```bash
# Arrêter et supprimer tout
docker-compose down -v
docker system prune -f
```

## 📈 Performance

### Optimisations
- **Connection pooling**: Configuré dans SQLAlchemy
- **Health checks**: Intervalle optimisé
- **Load balancing**: Répartition avec Nginx
- **Monitoring**: Fréquence ajustable (30 secondes par défaut)

### Scalabilité
- **Horizontal scaling**: Ajoutez des instances `app3`, `app4`
- **Vertical scaling**: Augmentez les ressources Docker
- **Database scaling**: Configurez PostgreSQL en cluster

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit les changements
4. Push vers la branche
5. Créer une Pull Request

## 📝 License

Ce projet est soumis à la license MIT - voir le fichier [LICENSE](LICENSE) pour les détails.

## 🎯 Objectifs Pédagogiques

Ce projet démontre la maîtrise de:

- ✅ **Développement Flask**: Application web complète
- ✅ **Conteneurisation**: Docker et Docker Compose
- ✅ **Réseaux**: Communication inter-services, load balancing
- ✅ **Base de données**: PostgreSQL conteneurisée
- ✅ **Monitoring**: Surveillance système et réseau
- ✅ **API REST**: Endpoints pour l'échange de données
- ✅ **Architecture distribuée**: Multi-conteneurs

---

**Auteur**: ISAAC - L3 RI ISI Keur Massar  
**Projet**: Examen DEVNET  
**Date**: Mars 2026
