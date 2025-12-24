# Docker Quick Start Guide

## Prerequisites

- Docker Desktop installed (Docker Engine + Docker Compose)
- At least 8GB RAM available for Docker
- 10GB free disk space

## Quick Start

```bash
# 1. Copy environment template
cp .env.docker .env

# 2. Start all services
docker-compose up -d

# 3. Monitor startup (takes 5-10 minutes first time)
docker-compose logs -f fastapi

# 4. Wait for "Starting FastAPI server..." message

# 5. Access application
# - Web UI: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

## Common Commands

```bash
# View logs
docker-compose logs -f [service]    # postgres, weaviate, ollama, fastapi

# Check service status
docker-compose ps

# Restart service
docker-compose restart fastapi

# Stop all services
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove everything (deletes data)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build fastapi
```

## Troubleshooting

### Service won't start

```bash
docker-compose logs [service]
docker-compose restart [service]
```

### Port already in use

```bash
lsof -i :8000    # FastAPI
lsof -i :5432    # PostgreSQL
lsof -i :8080    # Weaviate
lsof -i :11434   # Ollama
```

### Reset everything

```bash
docker-compose down -v
docker-compose up -d
```

### Out of memory

Increase Docker memory limit in Docker Desktop Settings > Resources

Or use lighter model:

```bash
echo "OLLAMA_MODEL=qwen2.5:1.5b" >> .env
docker-compose restart ollama
```

## Environment Variables

Edit `.env` file to customize:

```bash
# Database
POSTGRES_DB=policy_rag
POSTGRES_USER=policy_user
POSTGRES_PASSWORD=policy_pass

# LLM Model
OLLAMA_MODEL=qwen2.5:3b

# Logging
LOG_LEVEL=INFO
```

## Service Endpoints

- **FastAPI:** http://localhost:8000
- **PostgreSQL:** localhost:5432
- **Weaviate:** http://localhost:8080
- **Ollama:** http://localhost:11434

## Data Persistence

Data is stored in Docker volumes:

- `postgres_data` - Database
- `weaviate_data` - Vector index
- `ollama_data` - LLM models
- `./data` - Documents & chunks
- `./logs` - Application logs

## Testing in Docker

```bash
# Run tests inside container
docker-compose exec fastapi python -m pytest tests/

# Run specific test file
docker-compose exec fastapi python -m pytest tests/test_api_endpoints.py -v
```

## Backup & Restore

```bash
# Backup database
docker-compose exec postgres pg_dump -U policy_user policy_rag > backup.sql

# Restore database
docker-compose exec -T postgres psql -U policy_user policy_rag < backup.sql
```

## Production Checklist

- [ ] Change default passwords in `.env`
- [ ] Enable authentication for Weaviate
- [ ] Add HTTPS/TLS (nginx reverse proxy)
- [ ] Configure resource limits
- [ ] Set up monitoring (health checks, logs)
- [ ] Enable automatic backups
- [ ] Use secrets management (not plain .env)
- [ ] Configure restart policies
- [ ] Set up log rotation
- [ ] Test disaster recovery

## GPU Support (Optional)

For faster LLM inference with NVIDIA GPU:

1. Install nvidia-docker2
2. Uncomment GPU section in `docker-compose.yml`
3. Restart services

```bash
docker-compose down
docker-compose up -d
```

## Support

See full documentation in README.md Step 8 for:

- Detailed architecture
- Volume management
- Performance optimization
- Security hardening
- Deployment options
- Scaling strategies
