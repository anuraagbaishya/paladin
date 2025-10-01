# Paladin

## Features
1. Fetch GHSAs and view them in the web UI
2. Search based on any word in the GHSA
3. Initiate a Semgrep scan from the web UI for repos that were discernable from GHSAs
4. View SARIF output of the scans using a custom viewer
5. View source files referenced in SARIF findings
6. Suppress individual findings from SARIF scans
7. Review findings using Google Gemini

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

### MongoDB
Paladin uses MongoDB as its database. To run Paladin you will have to set up MongoDB on your system.

## Usage

Run the Flask app:

```bash
poetry run python app.py
```

Open your browser at your Paladin address (default: [http://127.0.0.1:9001](http://127.0.0.1:9001)) to access the web UI.

### Scanning

- Click the **Scan** button next to a repository to start a scan.
- Scan progress is displayed with a spinner, and completion is indicated with a tick.
- Scan results are written to MongoDB.
- Scan results can be viewed using the **SARIF viewer** by clicking the **Show Scans** button and then selecting a scan result.

### SARIF Viewer

The SARIF Viewer provides these functionalities for each finding:
- A **View File** button that opens the source file in an embedded code viewer.
- A **Suppress** button that hides finding from the UI and marks it as suppressed in the backend.
    - Suppressed findings will not be shown in future views.
- An **AI Review** button that uses Google Gemini to review the finding

### AI Review
- To use Google Gemini, an API key is required. See [this doc](https://ai.google.dev/gemini-api/docs/api-key) on generating a key. Once you have the key, add it to your `config.toml` under `tokens` -> `gemini_api_key`.
- By default Paladin uses `gemini-2.5-flash-lite` but this can be configured in `config.toml` under `settings` -> `gemini_model`.
- Currently only single file analysis is supported. This means only the file where the finding was reported will be sent as context to Gemini.

### Refreshing GHSAs

- Click the refresh button on the top toolbar.
- The default timespan to fetch GHSAs is 7 days from the current day, but this can be changed by clicking the days part of the button and setting your desired timespan.
- This uses GitHub APIs, so a GitHub token must be added to `config.toml` for this to work.

### TO DO:
- Add ability to toggle viewing suppressed results at rule level. 
    - If suppressed findings are being shown, change the suppress button to unsuppress. 
    - Update the suppress API to accept a suppress param which can be set to true or false to suppress / unsuppress. The backend function already implements suppress / unsuppress functionality
- Add a feature to add repos directly to scan instead of requiring to add the repo from Github security advisory reports.