# Mastarr Deployment Guide

## Changes Made

This guide documents the updates made to use a local PostgreSQL container and port 2112.

---

## Summary of Changes

### 1. PostgreSQL Container Added
- Added `postgres` service to `docker-compose.yml`
- Uses PostgreSQL 15 Alpine image
- Data persisted in `postgres_data` volume
- Connected via internal network `mastarr_internal`

### 2. Port Changed to 2112
- Mastarr now runs on port **2112** (was 8000)
- Updated in:
  - `docker-compose.yml`
  - `Dockerfile`
  - `main.py`
  - `README.md`

### 3. Database Connection Updated
- Removed Supabase dependency
- Updated `models/database.py` to connect to local PostgreSQL
- Added PostgreSQL environment variables to `.env`

---

## Configuration

### Environment Variables (.env)

```env
# PostgreSQL Database Configuration
POSTGRES_USER=mastarr
POSTGRES_PASSWORD=mastarr_secure_password
POSTGRES_DB=mastarr
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Database URL (constructed automatically)
DATABASE_URL=postgresql://mastarr:mastarr_secure_password@postgres:5432/mastarr

# Application Configuration
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

**⚠️ IMPORTANT**: Change `POSTGRES_PASSWORD` before deploying to production!

---

## Deployment Steps

### 1. Clone/Update Repository
```bash
cd /path/to/mastarr
git pull  # or clone if first time
```

### 2. Update Environment Variables
```bash
nano .env
# Change POSTGRES_PASSWORD to a secure password
```

### 3. Build and Start Services
```bash
docker-compose down  # Stop existing containers
docker-compose up -d --build
```

### 4. Verify Services
```bash
# Check all services are running
docker-compose ps

# Should see:
# mastarr           running
# mastarr_postgres  running
```

### 5. Check Logs
```bash
# Mastarr logs
docker logs mastarr -f

# PostgreSQL logs
docker logs mastarr_postgres -f
```

### 6. Load Blueprints
```bash
docker exec -it mastarr python load_blueprints.py
```

### 7. Access Mastarr
Open browser to: **http://localhost:2112**

Or if on remote server: **http://your-server-ip:2112**

---

## Services

### Mastarr
- **Port**: 2112
- **Container**: `mastarr`
- **Networks**: `mastarr_net` (external), `mastarr_internal` (with postgres)

### PostgreSQL
- **Port**: 5432 (internal only, not exposed to host)
- **Container**: `mastarr_postgres`
- **Volume**: `postgres_data`
- **Network**: `mastarr_internal`

---

## Volumes

```bash
# PostgreSQL data
docker volume inspect mastarr_postgres_data

# Application data
./data/       # SQLite metadata (if any)
./logs/       # Application logs
./stacks/     # Docker compose files for installed apps
```

---

## Networks

### mastarr_net (External)
- Shared network for all installed apps
- IP Range: 10.21.12.0/26
- Mastarr IP: 10.21.12.2

### mastarr_internal (Internal)
- Private network for Mastarr ↔ PostgreSQL
- Not accessible to installed apps
- Provides database isolation

---

## Troubleshooting

### Database Connection Issues

**Symptom**: Can't connect to database

**Solution**:
```bash
# Check postgres is running
docker logs mastarr_postgres

# Check database URL
docker exec -it mastarr env | grep DATABASE_URL

# Verify connection
docker exec -it mastarr_postgres psql -U mastarr -d mastarr -c "\dt"
```

### Port Already in Use

**Symptom**: Port 2112 is already in use

**Solution**:
```bash
# Find what's using the port
sudo lsof -i :2112

# Either stop that service or change Mastarr's port
# Edit docker-compose.yml: "2113:2112"
```

### Mastarr Won't Start

**Symptom**: Mastarr container exits immediately

**Solution**:
```bash
# Check logs
docker logs mastarr

# Common issues:
# 1. Database not ready - wait for postgres healthcheck
# 2. Missing environment variables - check .env
# 3. Permission issues - check volumes
```

### Reset Database

**Warning**: This deletes all data!

```bash
# Stop services
docker-compose down

# Remove postgres volume
docker volume rm mastarr_postgres_data

# Restart
docker-compose up -d
```

---

## Backup and Restore

### Backup Database
```bash
docker exec mastarr_postgres pg_dump -U mastarr mastarr > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker exec -i mastarr_postgres psql -U mastarr mastarr
```

### Backup Everything
```bash
# Database
docker exec mastarr_postgres pg_dump -U mastarr mastarr > backup.sql

# Compose files
tar -czf stacks_backup.tar.gz ./stacks/

# Data
tar -czf data_backup.tar.gz ./data/
```

---

## Security Notes

1. **Change Default Password**: Update `POSTGRES_PASSWORD` in `.env`
2. **Firewall**: Only expose port 2112 to trusted networks
3. **Reverse Proxy**: Use nginx/traefik with SSL in production
4. **Volume Permissions**: Ensure proper file permissions on volumes
5. **Network Isolation**: PostgreSQL is not exposed to host (good!)

---

## Upgrading

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Check logs
docker logs mastarr -f
```

Database migrations will run automatically on startup.

---

## Monitoring

### Health Check
```bash
curl http://localhost:2112/health
# Should return: {"status":"healthy"}
```

### Database Size
```bash
docker exec mastarr_postgres psql -U mastarr -d mastarr -c "SELECT pg_size_pretty(pg_database_size('mastarr'));"
```

### Container Stats
```bash
docker stats mastarr mastarr_postgres
```

---

## Production Checklist

- [ ] Changed default PostgreSQL password
- [ ] Set up firewall rules
- [ ] Configured reverse proxy with SSL
- [ ] Set up automated backups
- [ ] Configured log rotation
- [ ] Monitored disk space
- [ ] Tested disaster recovery
- [ ] Documented custom configuration

---

## Support

Check logs first:
```bash
docker logs mastarr -f
docker logs mastarr_postgres -f
```

Common files to check:
- `.env` - Environment variables
- `docker-compose.yml` - Service configuration
- `models/database.py` - Database connection
- `HOOKS_OVERVIEW.md` - App hooks system
