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

### 1. Clone the repository

```bash
git clone [https://github.com/anuraagbaishya/paladin.git](https://github.com/anuraagbaishya/paladin.git)
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
```

### 1. Build frontend and backend containers

```bash
make up
```

### 2. Access the app

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
* An AI Review button that uses Google Gemini to review the finding

### AI Review
* To use Google Gemini, an API key is required. See this doc on generating a key. Once you have the key, add it to your config.toml under tokens -> gemini_api_key.
* By default Paladin uses gemini-2.5-flash-lite but this can be configured in config.toml under settings -> gemini_model.
* Currently only single file analysis is supported. This means only the file where the finding was reported will be sent as context to Gemini.

### Refreshing GHSAs
* Click the refresh button on the top toolbar.
* The default timespan to fetch GHSAs is 7 days from the current day, but this can be changed by clicking the days part of the button and setting your desired timespan.
* This uses GitHub APIs, so a GitHub token must be added to config.toml for this to work.

## TO DO

* Add ability to toggle viewing suppressed results at rule level
* Add a feature to add repos directly to scan instead of requiring GitHub security advisory reports
