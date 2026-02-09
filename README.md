# Paladin

## Features

1. Fetch GHSAs and view them in the web UI
2. Search based on any word in the GHSA
3. Initiate a Semgrep scan from the web UI for repos that were discernable from GHSAs
4. View SARIF output of the scans using a custom viewer
5. View source files referenced in SARIF findings
6. Suppress individual findings from SARIF scans
7. Review findings using Claude Code AI

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/anuraagbaishya/paladin.git
cd paladin
```

### 2. Configure the app

1. Create a `config.toml` from `config.toml.sample`
2. Add the required configurations. Minimal required config is:
```
[paths]
semgrep_rules_dir = ""
clone_base_dir = ""

[tokens]
github_token = ""

[deployment]
host = "127.0.0.1"
port = 9001
workers = 4
claude_bridge_port = 3000
```

### 3. Install prerequisites

Install `toml-cli` to read `config.toml` from `Makefile`:
```
pip install toml-cli
```

Install [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) for AI-powered finding reviews:
```
npm install -g @anthropic-ai/claude-code
```

### 4. Build containers and run Paladin

```bash
make build && make up
```

This starts the Docker containers and the bridge server on the host.

### 5. Access the app

* Open `http://<HOST>:<PORT>` as configured in `config.toml` under `[deployment]`.
* Default: [`http://127.0.0.1:9001`](http://127.0.0.1:9001)

Data is stored in a MongoDb container which uses volumes for persistence.

## Features

### Scanning
* Click the Scan button next to a repository to start a scan.
* Results can be viewed using the SARIF viewer by clicking the Show Scans button and then selecting a scan result.

### SARIF Viewer
The SARIF Viewer provides these functionalities for each finding:

* A View File button that opens the source file in an embedded code viewer.
* A Suppress button that hides finding from the UI and marks it as suppressed in the backend.
* Suppressed findings will not be shown in future views.
* An AI Review button that uses Claude Code to review the finding

### AI Review
* AI Review uses Claude Code via a bridge server that runs on the host machine (outside Docker).
* The bridge server is started automatically by `make up` and listens on the port configured in `config.toml` under `deployment.claude_bridge_port`.
* **Prerequisite:** [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) must be installed and authenticated on the host machine.
* The bridge server sends the finding details and repository path to Claude Code, which analyzes the code in context and returns a structured verdict (true positive / false positive with reasoning).
* Reviews may take a few minutes as Claude Code performs deep analysis of the codebase.

### Refreshing GHSAs
* Click the refresh button on the top toolbar.
* The default timespan to fetch GHSAs is 7 days from the current day, but this can be changed by clicking the days part of the button and setting your desired timespan.
* This uses GitHub APIs, so a GitHub token must be added to config.toml for this to work.

## TO DO

* Add ability to toggle viewing suppressed results at repo level
