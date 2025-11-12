.PHONY: build run clean help logs shell up down db-console db-logs db-reset bot-up bot-down bot-logs bot-restart

# Docker image name
IMAGE_NAME := willhaben-scraper
CONTAINER_NAME := willhaben-scraper-run

# Docker Compose project name
COMPOSE_PROJECT := willhaben

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@echo ''
	@echo 'Docker Compose (with database):'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'up|down|db-' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ''
	@echo 'Legacy Docker (without database):'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v -E 'up|down|db-' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME) .

run: ## Run scraper in Docker and extract CSV to current directory
	@echo "Running scraper in Docker..."
	@docker run --rm \
		--name $(CONTAINER_NAME) \
		-v "$(PWD)/output:/app/output" \
		$(IMAGE_NAME)
	@echo ""
	@echo "✓ CSV file saved to: ./output/willhaben_listings.csv"

run-verbose: ## Run scraper with verbose logging
	@echo "Running scraper with verbose logging..."
	@docker run --rm \
		--name $(CONTAINER_NAME) \
		-v "$(PWD)/output:/app/output" \
		$(IMAGE_NAME) \
		python parser.py --verbose --out /app/output/willhaben_listings.csv

shell: ## Open shell in Docker container
	@docker run --rm -it \
		--name $(CONTAINER_NAME) \
		-v "$(PWD)/output:/app/output" \
		--entrypoint /bin/bash \
		$(IMAGE_NAME)

clean: ## Remove Docker image and output files
	@echo "Cleaning up..."
	@docker rmi -f $(IMAGE_NAME) 2>/dev/null || true
	@rm -rf output/*.csv 2>/dev/null || true
	@echo "✓ Cleanup complete"

rebuild: clean build ## Clean and rebuild Docker image

logs: ## Show logs from last run (if container is still running)
	@docker logs $(CONTAINER_NAME)

all: ## Build and run scraper with database (docker-compose)
	@echo "Building and running scraper with database..."
	docker-compose up --build scraper

start-all: ## Run initial scrape and start bot in background (complete setup)
	@echo "==> Step 1: Starting database..."
	@docker-compose up --build -d postgres
	@echo "Waiting for database to be ready..."
	@sleep 3
	@echo ""
	@echo "==> Step 2: Running initial scrape to populate database..."
	@docker-compose run --rm scraper python3 main.py --download-photos
	@echo ""
	@echo "==> Step 3: Starting Telegram bot in background..."
	@docker-compose up --build -d bot
	@echo ""
	@echo "✓ All services started!"
	@echo "  - Database: running"
	@echo "  - Initial scrape: complete"
	@echo "  - Telegram bot: running in background"
	@echo ""
	@echo "Useful commands:"
	@echo "  make bot-logs     - View bot logs"
	@echo "  make db-console   - Connect to database"
	@echo "  make down         - Stop all services"

# ==================== Docker Compose Commands ====================

up: ## Start database and run scraper with docker-compose
	@echo "Starting services with docker-compose..."
	docker-compose up --build

up-detached: ## Start database in background
	@echo "Starting database in background..."
	docker-compose up -d postgres
	@echo "✓ Database is starting. Use 'make db-console' to connect."

down: ## Stop all docker-compose services
	@echo "Stopping all services..."
	docker-compose down
	@echo "✓ Services stopped"

db-console: ## Enter PostgreSQL console (psql)
	@echo "Connecting to database..."
	@docker-compose exec postgres psql -U willhaben_user -d willhaben

db-logs: ## Show PostgreSQL logs
	@docker-compose logs -f postgres

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "⚠️  This will delete all database data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		echo "✓ Database reset complete"; \
	else \
		echo "Cancelled"; \
	fi

run-with-db: up-detached ## Run scraper locally with database in background
	@echo "Waiting for database to be ready..."
	@sleep 3
	@echo "Running scraper..."
	python3 main.py
	@echo ""
	@echo "✓ Scraper complete. Database still running."
	@echo "  Use 'make db-console' to view data"
	@echo "  Use 'make down' to stop database"

test-flow: ## Test new listing detection flow: down -> all -> delete top listing -> start bot with notifications
	@echo "==> Step 1: Stopping services..."
	@$(MAKE) down
	@echo ""
	@echo "==> Step 2: Building and running initial scrape..."
	@$(MAKE) all
	@echo ""
	@echo "==> Step 3: Deleting top listing from database..."
	@docker-compose exec -T postgres psql -U willhaben_user -d willhaben -c "\
		DELETE FROM listings \
		WHERE link = (SELECT link FROM listings ORDER BY first_seen_at DESC LIMIT 1) \
		RETURNING listing_name, link;" | tee /tmp/deleted_listing.txt
	@echo ""
	@echo "==> Step 4: Cleaning photos directory..."
	@rm -rf photos/*
	@echo "✓ Photos directory cleaned"
	@echo ""
	@echo "==> Step 5: Starting Telegram bot (will detect deleted listing as new)..."
	@echo "⚠️  Bot will run continuously. Press Ctrl+C when you verify the Telegram notification."
	@echo "⚠️  Check your Telegram channel for the notification with photos in media group."
	@echo ""
	@docker-compose up --build -d postgres
	@sleep 3
	@docker-compose up --build bot
	@echo ""
	@echo "✓ Test flow stopped (bot shut down)"
	@echo "  Use 'make bot-up-detached' to restart bot in background"
	@echo "  Use 'make down' to stop all services"

# ==================== Telegram Bot Commands ====================

bot-up: ## Start Telegram bot (runs continuously, checking for new listings)
	@echo "Starting Telegram bot..."
	@echo "⚠️  Make sure to set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first!"
	docker-compose up --build -d postgres
	@echo "Waiting for database to be ready..."
	@sleep 3
	docker-compose up --build bot

bot-down: ## Stop Telegram bot
	@echo "Stopping Telegram bot..."
	docker-compose stop bot
	@echo "✓ Bot stopped"

bot-logs: ## Show Telegram bot logs (follow mode)
	@docker-compose logs -f bot

bot-restart: ## Restart Telegram bot
	@echo "Restarting Telegram bot..."
	docker-compose restart bot
	@echo "✓ Bot restarted"

bot-up-detached: ## Start Telegram bot in background
	@echo "Starting Telegram bot in background..."
	@echo "⚠️  Make sure to set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first!"
	docker-compose up --build -d postgres bot
	@echo "✓ Bot started in background"
	@echo "  Use 'make bot-logs' to view logs"
	@echo "  Use 'make bot-down' to stop"
