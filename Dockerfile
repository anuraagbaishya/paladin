# ---- Stage 1: Build frontend ----
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python backend ----
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential netcat-openbsd git \
    && rm -rf /var/lib/apt/lists/*

# Get the scc binary - used to detect languages in the project
RUN curl -L https://github.com/boyter/scc/releases/download/v3.5.0/scc_Linux_arm64.tar.gz \
    | tar -xz -C /usr/local/bin scc

# Install Poetry and backend dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root

# Configure semgrep
RUN pip install semgrep
ARG SEMGREP_RULES_DIR
RUN git clone https://github.com/semgrep/semgrep-rules $SEMGREP_RULES_DIR

# Install Gunicorn
RUN pip install gunicorn

# Copy backend code
COPY . .

# Copy frontend build into static folder
COPY --from=frontend-build /app/static/js ./static/js

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
