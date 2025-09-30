# Semgrep Runner

## Features
1. Fetch GHSAs and view them in the web UI
2. Search based on any word in the GHSA
3. Initiate a Semgrep scan from the web UI for repos that were discernable from GHSAs
4. View SARIF output of the scans using a custom viewer
5. View source files referenced in SARIF findings
6. Suppress individual findings from SARIF scans

## Installation

1. Clone this repository:

```bash
git clone https://github.com/anuraagbaishya/paladin.git
cd paladin
```

2. Install dependencies using Poetry:

```bash
poetry install --no-root
```

3. Build the front-end:

```bash
cd frontend
npm install
npm run build
```

4. Configure the app:
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
- Scan results can be viewed using the **SARIF viewer** by clicking the **Show Scans** button and then selecting a scan result.

### SARIF Viewer

The SARIF Viewer provides these functionalities for each finding
- A **View File** button that opens the source file in an embedded code viewer.
- A **Suppress** button next to the file viewer button that hides finding from the UI and marks it as suppressed in the backend.
    - Suppressed findings will not be shown in future views.

### Refreshing GHSAs

- Click the refresh button on the top toolbar.
- The default timespan to fetch GHSAs is 7 days from the current day, but this can be changed by clicking the days part of the button and setting your desired timespan.
- This uses GitHub APIs, so a GitHub token must be added to `config.toml` for this to work.
