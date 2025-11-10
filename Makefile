.PHONY: build run clean help logs shell

# Docker image name
IMAGE_NAME := willhaben-scraper
CONTAINER_NAME := willhaben-scraper-run

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

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

all: build run ## Build and run scraper
