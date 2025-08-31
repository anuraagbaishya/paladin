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
- Scan results are written to MongoDB.
- Scan results can be using the Sarif viewer by clickinh on **Show Scans** button and the clicking on a scan result.