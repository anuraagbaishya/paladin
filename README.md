# Semgrep Runner

A Python tool that runs Semgrep on GitHub repositories and provides a modern web UI to view scan results.

## Features

- Detect vulnerabilities in repositories using Semgrep.
- Web interface with job-based scanning.
- Dark mode UI with expandable details per report.
- Stores scan metadata in MongoDB.
- Uses Poetry for dependency management.

## Installation

1. Clone this repository:

```bash
git clone https://github.com/anuraagbaishya/semgrep-runner.git
cd semgrep-runner
```

2. Install dependencies using Poetry:

```bash
poetry install --no-root
```

## Usage

Run the Flask app:

```bash
poetry run python app.py
```

Open your browser at [http://127.0.0.1:9001](http://127.0.0.1:9001) to access the web UI.

### Scanning

- Click the **Scan** button next to a repository to start a scan.
- Scan progress is displayed with a spinner, and completion is indicated with a tick.
- Scan metadata is automatically stored in MongoDB.

## Project Structure

```
semgrep-runner/
├─ app.py           # Flask app and backend APIs
├─ scanner/         # Scan logic (clone, run Semgrep, etc.)
├─ static/          # JS, CSS, images
├─ templates/       # HTML templates
├─ pyproject.toml   # Poetry configuration
└─ README.md
```

## Dependencies

- Python 3.13+
- Flask 3.1.2
- GitPython 3.1.45
- PyMongo 4.14.1
- Semgrep (installed separately)

## Notes

- Poetry manages dependencies; the project itself does not need to be installed as a package.
- Semgrep rules should be placed in `SEMGREP_RULES_DIR`.
