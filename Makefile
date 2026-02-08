PORT := $(shell toml get --toml-path config.toml deployment.port)
HOST := $(shell toml get --toml-path config.toml deployment.host)
WORKERS := $(shell toml get --toml-path config.toml deployment.workers)
SEMGREP_RULES_DIR := $(shell toml get --toml-path config.toml paths.semgrep_rules_dir)
CLONE_BASE_DIR := $(shell toml get --toml-path config.toml paths.clone_base_dir)
MONGO_HOST := $(shell toml get --toml-path config.toml mongo.host 2>/dev/null || echo mongo)
MONGO_PORT := $(shell toml get --toml-path config.toml mongo.port 2>/dev/null || echo 27017)
CLAUDE_BRIDGE_PORT := $(shell toml get --toml-path config.toml deployment.claude_bridge_port)
MONGO_HOST_PORT := $(shell echo 27018)

COMPOSE_ENV = HOST_PORT=$(PORT) CONTAINER_PORT=$(PORT) WORKERS=$(WORKERS) MONGO_HOST=$(MONGO_HOST) MONGO_PORT=$(MONGO_PORT) MONGO_HOST_PORT=$(MONGO_HOST_PORT) CLONE_BASE_DIR=$(CLONE_BASE_DIR) CLAUDE_BRIDGE_PORT=$(CLAUDE_BRIDGE_PORT)

ifndef NO_MONGO
PROFILE_FLAG = --profile mongo
endif

build:
	@echo "Building Paladin backend with Semgrep rules path: $(SEMGREP_RULES_DIR)"
	$(COMPOSE_ENV) docker compose build --build-arg SEMGREP_RULES_DIR=$(SEMGREP_RULES_DIR) paladin

up:
	@echo "Starting Paladin on host $(HOST) port $(PORT) with $(WORKERS) workers..."
	mkdir -p $(CLONE_BASE_DIR)
	$(COMPOSE_ENV) docker compose $(PROFILE_FLAG) up -d
	@echo "Starting bridge server at localhost:$(CLAUDE_BRIDGE_PORT)"
	cd bridge_server && poetry run flask --app server run --host 0.0.0.0 --port $(CLAUDE_BRIDGE_PORT)

down:
	@echo "Stopping Paladin..."
	$(COMPOSE_ENV) docker compose --profile mongo down

logs:
	$(COMPOSE_ENV) docker compose logs -f paladin

rebuild:
	@echo "Rebuilding Paladin backend..."
	$(COMPOSE_ENV) docker compose build --no-cache --build-arg SEMGREP_RULES_DIR=$(SEMGREP_RULES_DIR) paladin
	$(COMPOSE_ENV) docker compose $(PROFILE_FLAG) up --force-recreate

shell:
	$(COMPOSE_ENV) docker compose exec paladin sh
