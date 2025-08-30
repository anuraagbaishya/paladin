# Semgrep Runner

A Python tool that runs Semgrep on GitHub repositories and provides a web UI to view scan results.

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

3. Build the front-end
```bash
cd frontend
npm install
npm run build
```

4. Configure the app
    1. Create a `config.toml` from `config.toml.sample`
    2. Add the required configurations as appropriate

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
