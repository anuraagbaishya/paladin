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
    refresher = Refresher(mongo_utils)

    threading.Thread(target=refresher.refresh, daemon=True).start()

    return jsonify({"status": "OK"})


if __name__ == "__main__":
    verifier: ConfigVerifier = ConfigVerifier("config.toml")
    config = verifier.verify()

    if not config:
        sys.exit(1)

    mongo_utils: MongoUtils = MongoUtils(config)
    deployment = config["deployment"]

    scanner: Scanner = Scanner(config, mongo_utils)
    refresher: Refresher = Refresher(mongo_utils)

    app.run(debug=True, host=deployment["host"], port=deployment["port"])
