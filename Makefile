PORT := $(shell toml get --toml-path config.toml deployment.port)
HOST := $(shell toml get --toml-path config.toml deployment.host)
WORKERS := $(shell toml get --toml-path config.toml deployment.workers)
SEMGREP_RULES_DIR := $(shell toml get --toml-path config.toml paths.semgrep_rules_dir)
CLONE_BASE_DIR := $(shell toml get --toml-path config.toml paths.clone_base_dir)
HOST_REPOS_DIR := $(shell echo ~/.paladin/repos)

up:
	@echo "Building Paladin backend with Semgrep rules path: $(SEMGREP_RULES_DIR)"
	HOST_PORT=$(PORT) CONTAINER_PORT=$(PORT) WORKERS=$(WORKERS) \
	docker-compose build --build-arg SEMGREP_RULES_DIR=$(SEMGREP_RULES_DIR) paladin
	@echo "Starting Paladin on host $(HOST) port $(PORT) with $(WORKERS) workers..."
	mkdir -p $(HOST_REPOS_DIR)
	HOST_PORT=$(PORT) CONTAINER_PORT=$(PORT) WORKERS=$(WORKERS) \
	docker-compose run --remove-orphans --service-ports \
		-v $(HOST_REPOS_DIR):$(CLONE_BASE_DIR) \
		paladin

down:
	@echo "Stopping Paladin..."
	docker-compose down

logs:
	docker-compose logs -f paladin

rebuild:
	@echo "Rebuilding Paladin backend..."
	docker-compose build --no-cache --build-arg SEMGREP_RULES_DIR=$(SEMGREP_RULES_DIR) paladin
	docker-compose up --force-recreate paladin

shell:
	docker-compose exec paladin sh
