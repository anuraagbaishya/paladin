PORT := $(shell toml get --toml-path config.toml deployment.port)
HOST := $(shell toml get --toml-path config.toml deployment.host)
WORKERS := $(shell toml get --toml-path config.toml deployment.workers)
SEMGREP_RULES_DIR := $(shell toml get --toml-path config.toml paths.semgrep_rules_dir)
CLONE_BASE_DIR := $(shell toml get --toml-path config.toml paths.clone_base_dir)
MONGO_HOST := $(shell toml get --toml-path config.toml mongo.host 2>/dev/null || echo mongo)
MONGO_PORT := $(shell toml get --toml-path config.toml mongo.port 2>/dev/null || echo 27017)
MONGO_HOST_PORT := $(shell echo 27018)
HOST_REPOS_DIR := $(shell echo ~/.paladin/repos)

COMPOSE_ENV = HOST_PORT=$(PORT) CONTAINER_PORT=$(PORT) WORKERS=$(WORKERS) MONGO_HOST=$(MONGO_HOST) MONGO_PORT=$(MONGO_PORT) MONGO_HOST_PORT=$(MONGO_HOST_PORT) REPOS_DIR=$(HOST_REPOS_DIR) CLONE_BASE_DIR=$(CLONE_BASE_DIR)

ifndef NO_MONGO
PROFILE_FLAG = --profile mongo
endif

build:
	@echo "Building Paladin backend with Semgrep rules path: $(SEMGREP_RULES_DIR)"
	$(COMPOSE_ENV) docker compose build --build-arg SEMGREP_RULES_DIR=$(SEMGREP_RULES_DIR) paladin

up:
	@echo "Starting Paladin on host $(HOST) port $(PORT) with $(WORKERS) workers..."
	mkdir -p $(HOST_REPOS_DIR)
	$(COMPOSE_ENV) docker compose $(PROFILE_FLAG) up -d

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
