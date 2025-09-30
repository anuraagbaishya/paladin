import logging
import os
import sys
import threading
from pathlib import Path
from typing import Tuple, Union

from flask import Flask, Response, jsonify, render_template, request

from models.models import Job
from scanner.scan import Scanner
from refresher.refresh import Refresher

from utils.config_verifier import ConfigVerifier
from utils.mongo_utils import MongoUtils

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@app.route("/")
@app.route("/sarif/<id>")
def index(id=None) -> str:
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def submit_scan():
    data = request.json
    repo: str = data.get("repo")  # type: ignore
    repo_url: str = f"https://github.com/{repo}"

    if not repo_url:
        return jsonify({"error": "No repo provided"}), 400

    job: Job = mongo_utils.add_job_to_db(repo_url)

    # Run scan in background thread
    threading.Thread(
        target=scanner.run_scan_job, args=(job._id, repo_url), daemon=True
    ).start()

    return jsonify({"job_id": str(job._id)})


@app.route("/api/sarif/<id>")
def get_sarif(id: str) -> Response:
    data = mongo_utils.get_sarif_by_id(id)

    return jsonify(data)


@app.route("/api/sarif/<id>/suppress")
def suppress_finding(id: str) -> Response:
    fingerprint: str = request.args.get("fingerprint") or ""
    sarif_with_suppressions = scanner.mark_sarif_suppressed_by_fingerprint(
        id, fingerprint, True
    )

    return jsonify(sarif_with_suppressions)


@app.route("/api/scans/<path:repo>")
def get_scans_by_repo(repo) -> Response:
    results = mongo_utils.get_scans_from_db(repo)

    return jsonify(results)


@app.route("/api/vuln_reports")
def get_vuln_reports():
    reports = mongo_utils.get_reports_by_pkg()

    return jsonify(reports)


@app.route("/api/scans/delete/<id>", methods=["DELETE"])
def delete_scan_by_id(id) -> Union[Response, Tuple]:
    count = mongo_utils.delete_scan_by_id(id)
    if not count:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"status": "OK"})


@app.route("/scan_status/<job_id>")
def get_scan_status(job_id) -> Union[Response, Tuple]:
    job = mongo_utils.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(
        {"job_id": str(job._id), "status": job.status.value, "error": job.error}
    )


@app.route("/api/refresh_reports")
def refresh_reports() -> Union[Response, Tuple]:
    if not refresher.token:
        return jsonify({"error": "github token not configured"}), 400

    days: int = int(request.args.get("days", 7))

    threading.Thread(target=refresher.refresh, args=(days,), daemon=True).start()

    return jsonify({"status": "OK"})


@app.route("/api/file", methods=["POST"])
def get_file():
    data = request.get_json()
    if not data or "file_path" not in data:
        return jsonify({"error": "file_path missing in request body"}), 400

    file_path = data["file_path"]
    base_path = Path(config["paths"]["clone_base_dir"]).resolve()  # type: ignore
    requested_path = Path(file_path).resolve()

    # Ensure requested_path is inside base_path
    try:
        if os.path.commonpath([str(base_path), str(requested_path)]) != str(base_path):
            return jsonify({"error": "Invalid file path"}), 400
    except ValueError:
        return jsonify({"error": "Invalid file path"}), 400

    if not requested_path.is_file():
        return jsonify({"error": "File does not exist"}), 404

    try:
        with requested_path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {e}"}), 500

    return jsonify({"file": lines})


if __name__ == "__main__":
    verifier: ConfigVerifier = ConfigVerifier("config.toml")
    config = verifier.verify()

    if not config:
        sys.exit(1)

    mongo_utils: MongoUtils = MongoUtils(config)
    deployment = config["deployment"]
    github_token = config.get("tokens", {}).get("github_token", None)

    scanner: Scanner = Scanner(config, mongo_utils)
    refresher: Refresher = Refresher(github_token, mongo_utils)

    app.run(debug=True, host=deployment["host"], port=deployment["port"])
