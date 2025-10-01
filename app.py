import logging
import os
import sys
import threading
from dataclasses import asdict
from typing import Tuple, Union

from flask import Flask, Response, jsonify, render_template, request

from models.data_models import Job
from models.response_models import (FileError, FileResponse, ReviewError,
                                    ReviewResponse)
from refresher.refresh import Refresher
from scanner.scan import Scanner
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


@app.route("/api/scan/file", methods=["POST"])
def get_file() -> Union[Response, Tuple]:
    data = request.get_json()
    if not data or "filepath" not in data:
        return jsonify({"error": "filepath missing in request body"}), 400

    file_response: FileResponse = scanner.get_file(data["filepath"])

    if file_response.error:
        if file_response.error == FileError.INVALID_PATH:
            return jsonify(file_response.to_dict()), 400
        elif file_response.error == FileError.NOT_FOUND:
            return jsonify(file_response.to_dict()), 404
        else:
            return jsonify(file_response.to_dict()), 500

    return jsonify(file_response.to_dict()), 200


@app.route("/api/scan/review", methods=["POST"])
def review() -> Union[Response, Tuple]:
    data = request.get_json()
    if not data or "scan_id" not in data or "fingerprint_id" not in data:
        return jsonify({"error": "both scan_id and fingerprint_id are needed"}), 400

    review_response: ReviewResponse = scanner.review(
        data["scan_id"], data["fingerprint_id"]
    )

    if review_response.error:
        if review_response.error == ReviewError.SCAN_NOT_FOUND:
            return jsonify(review_response.to_dict()), 404
        else:
            return jsonify(review_response.to_dict()), 500

    return jsonify(review_response.to_dict()), 200


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
