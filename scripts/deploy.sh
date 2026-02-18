#!/bin/bash

# ==============================================
# Deployment Script for Saude Platform
# ==============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
BACKUP_DIR="./backups"
LOG_FILE="./logs/deploy-$(date +%Y%m%d-%H%M%S).log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if .env file exists
check_env() {
    log "Checking environment configuration..."
    if [ ! -f "$ENV_FILE" ]; then
        error ".env file not found! Please copy .env.example to .env and configure it."
    fi
    log "Environment file found ✓"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    mkdir -p logs backups nginx/conf.d nginx/ssl nginx/logs init-scripts scripts
    log "Directories created ✓"
}

# Backup database
backup_database() {
    log "Creating database backup..."
    mkdir -p "$BACKUP_DIR"
    
    if docker-compose ps postgres | grep -q "Up"; then
        BACKUP_FILE="$BACKUP_DIR/db-backup-$(date +%Y%m%d-%H%M%S).sql"
        docker-compose exec -T postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "$BACKUP_FILE" 2>/dev/null || warn "Database backup failed (might be first deployment)"
        
        if [ -f "$BACKUP_FILE" ]; then
            log "Database backed up to $BACKUP_FILE ✓"
            # Keep only last 7 backups
            ls -t "$BACKUP_DIR"/db-backup-*.sql | tail -n +8 | xargs -r rm
        fi
    else
        warn "PostgreSQL container not running, skipping backup"
    fi
}

# Pull latest code
pull_code() {
    log "Pulling latest code from repository..."
    if [ -d ".git" ]; then
        git pull origin main || warn "Git pull failed, continuing with local code"
        log "Code updated ✓"
    else
        warn "Not a git repository, skipping pull"
    fi
}

# Build images
build_images() {
    log "Building Docker images..."
    docker-compose build --no-cache backend || error "Build failed"
    log "Images built successfully ✓"
}

# Stop services
stop_services() {
    log "Stopping running services..."
    docker-compose down || warn "No services to stop"
    log "Services stopped ✓"
}

# Start services
start_services() {
    log "Starting services..."
    docker-compose up -d || error "Failed to start services"
    log "Services started ✓"
}

# Wait for services to be healthy
wait_for_health() {
    log "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose ps | grep -q "unhealthy"; then
            attempt=$((attempt + 1))
            echo -n "."
            sleep 2
        else
            echo ""
            log "All services are healthy ✓"
            return 0
        fi
    done
    
    error "Services failed to become healthy after $max_attempts attempts"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    docker-compose exec -T backend alembic upgrade head || error "Migration failed"
    log "Migrations completed ✓"
}

# Show service status
show_status() {
    log "Service Status:"
    docker-compose ps
    echo ""
    log "Logs location: ./logs/"
    log "Access points:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Flower (Celery): http://localhost:5555"
    echo "  - MinIO Console: http://localhost:9001"
    echo "  - Nginx: http://localhost"
}

# Cleanup old images
cleanup() {
    log "Cleaning up old Docker images..."
    docker image prune -f || warn "Image cleanup failed"
    log "Cleanup completed ✓"
}

# Main deployment flow
main() {
    log "=========================================="
    log "Starting Saude Platform Deployment"
    log "=========================================="
    
    check_env
    create_directories
    backup_database
    pull_code
    build_images
    stop_services
    start_services
    wait_for_health
    run_migrations
    cleanup
    show_status
    
    log "=========================================="
    log "Deployment completed successfully! 🚀"
    log "=========================================="
}

# Run main function
main "$@"
