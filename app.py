import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple, Union

from bson import ObjectId
from flask import Flask, Response, jsonify, render_template, request

from models.models import Job, JobStatus
from scanner.scan import (
    clean_sarif,
    clone_repo,
    delete_repo_if_no_findings,
    run_semgrep,
)
from utils.config_verifier import ConfigVerifier
from utils.mongo_utils import MongoUtils

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_scan_job(job_id: ObjectId, repo_url: str) -> None:
    """
    Runs the scan in a separate thread and updates job status.
    """

    mongo_utils.update_job_status(job_id, JobStatus.RUNNING)

    try:
        # Clone the repo
        repo_path: Path = clone_repo(repo_url)
        # Run semgrep (writing output to file as before)
        output: str = run_semgrep(repo_path)
        cleaned_output: Dict[str, Any] = clean_sarif(json.loads(output))

        repo_file_path: str = repo_path.name
        repo_name: str = f"{repo_url.split("/")[-2]}/{repo_url.split("/")[-1]}"

        mongo_utils.add_scan_result_to_db(repo_name, cleaned_output)

        write_sarif_to_file(cleaned_output, repo_file_path)

        # Delete if no findings
        delete_repo_if_no_findings(repo_path, output)

        # Mark job done
        mongo_utils.update_job_status(job_id, JobStatus.DONE)

    except Exception as e:
        mongo_utils.update_job_on_error(job_id, str(e))


def write_sarif_to_file(sarif: Dict[str, Any], repo: str) -> None:
    write_json: bool = config.get("settings", {}).get("write_sarif_to_file", None)  # type: ignore
    if not write_json:
        return

    sarif_write_dir: str = config.get("paths", {}).get("sarif_write_dir", "")  # type: ignore
    if not sarif_write_dir:
        sarif_write_path: Path = Path(".")
    else:
        sarif_write_path: Path = Path(sarif_write_dir)
        os.makedirs(sarif_write_path, exist_ok=True)

    timestamp: int = int(datetime.now(timezone.utc).timestamp())

    sarif_write_path = sarif_write_path / f"{repo}_{timestamp}.json"
    with open(sarif_write_path, "w+") as f:
        json.dump(sarif, f, indent=4)

    logging.info(f"Output written to {sarif_write_path}")


@app.route("/")
@app.route("/sarif/<id>")
def index(id=None) -> str:
    return render_template("index.html")


@app.route("/api/sarif/<id>")
def get_sarif(id: str) -> Response:
    data = mongo_utils.get_sarif_by_id(id)

    return jsonify(data)


@app.route("/api/scans/<path:repo>")
def get_scans_by_repo(repo) -> Response:
    results = mongo_utils.get_scans_from_db(repo)

    return jsonify(results)


@app.route("/api/vuln_reports")
def get_vuln_reports():
    reports = mongo_utils.get_reports_by_pkg()

    return jsonify(reports)


@app.route("/api/scan", methods=["POST"])
def submit_scan():
    data = request.json
    repo: str = data.get("repo")  # type: ignore
    repo_url: str = f"https://github.com/{repo}"

    if not repo_url:
        return jsonify({"error": "No repo provided"}), 400

    job: Job = mongo_utils.add_job_to_db(repo_url)

    # Run scan in background thread
    threading.Thread(target=run_scan_job, args=(job._id, repo_url), daemon=True).start()

    return jsonify({"job_id": str(job._id)})


@app.route("/scan_status/<job_id>")
def get_scan_status(job_id) -> Union[Response, Tuple]:
    job = mongo_utils.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(
        {"job_id": str(job._id), "status": job.status.value, "error": job.error}
    )


if __name__ == "__main__":
    verifier: ConfigVerifier = ConfigVerifier("config.toml")
    config = verifier.verify()

    if not config:
        sys.exit(1)

    mongo_utils: MongoUtils = MongoUtils(config)

    app.run(debug=True, port=9001)
