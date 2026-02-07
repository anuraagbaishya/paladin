import logging
import sys
import threading

from bson import ObjectId
from flask import Flask, Response, jsonify, render_template, request

from models.response_models import (
    FileError,
    FileResponse,
    JobResponse,
    ReviewError,
    ReviewResponse,
)
from refresher.refresh import Refresher
from scanner.scan import Scanner
from utils.config import Config
from utils.mongo_utils import MongoUtils

# --- Initialize app and logger ---
app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Initialize configuration and services at module level ---
try:
    config = Config("config.toml")
except (FileNotFoundError, ValueError, TypeError) as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

mongo_utils: MongoUtils = MongoUtils(config)
github_token = config.github_token if config.github_token else None

scanner: Scanner = Scanner(config, mongo_utils)
if github_token:
    refresher: Refresher = Refresher(github_token, mongo_utils)


# --- Routes ---
@app.route("/")
@app.route("/scans")
@app.route("/advisories")
@app.route("/scan/<path:repo>/<id>")
def index(repo=None, id=None) -> str:
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def submit_scan() -> tuple[Response, int]:
    data = request.json
    repo: str = data.get("repo")  # type: ignore
    repo_url: str = f"https://github.com/{repo}"

    if not repo_url:
        return jsonify({"error": "No repo provided"}), 400

    job: JobResponse = JobResponse(repo_url)
    job_id: ObjectId = mongo_utils.add_job_to_db(job)
    job._id = job_id

    threading.Thread(
        target=scanner.run_scan_job, args=(job._id, repo_url), daemon=True
    ).start()

    return jsonify(job.to_dict()), 200


@app.route("/api/scan/<path:repo>/<id>")
def get_scan(repo: str, id: str) -> tuple[Response, int]:
    results = mongo_utils.get_results_by_scan_id(id)
    if results:
        serialized = []
        for r in results:
            d = r.result.to_dict()  # type: ignore
            d["suppressed"] = r.suppressed
            d["severity"] = r.severity
            d["aiReview"] = r.ai_review.model_dump()
            serialized.append(d)
        return jsonify({"scan_id": id, "repo": repo, "results": serialized}), 200

    return jsonify({"error": "scan not found"}), 404


@app.route("/api/sarif/<id>/suppress")
def suppress_finding(id: str) -> Response:
    fingerprint: str = request.args.get("fingerprint") or ""
    sarif_with_suppressions = scanner.mark_sarif_suppressed_by_fingerprint(
        id, fingerprint, True
    )
    return jsonify(sarif_with_suppressions)


@app.route("/api/scans")
def get_all_scans() -> Response:
    results = mongo_utils.get_all_scans()
    return jsonify(results)


@app.route("/api/scans/<path:repo>")
def get_scans_by_repo(repo) -> Response:
    results = mongo_utils.get_scans_by_repo(repo)
    return jsonify(results)


@app.route("/api/reports")
def get_reports():
    reports = mongo_utils.get_reports_by_pkg()
    return jsonify(reports)


@app.route("/api/scans/delete/<id>", methods=["DELETE"])
def delete_scan_by_id(id) -> tuple[Response, int]:
    count = mongo_utils.delete_scan_by_id(id)
    if not count:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"status": "OK"}), 200


@app.route("/api/job_status/<job_id>")
def get_scan_status(job_id) -> tuple[Response, int]:
    job = mongo_utils.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job.to_dict()), 200


@app.route("/api/refresh_reports")
def refresh_reports() -> tuple[Response, int]:
    if not refresher.token:
        return jsonify({"error": "github token not configured"}), 400

    days: int = int(request.args.get("days", 7))

    job: JobResponse = JobResponse()
    job_id: ObjectId = mongo_utils.add_job_to_db(job)
    job._id = job_id

    threading.Thread(
        target=refresher.refresh, args=(job._id, days), daemon=True
    ).start()

    return jsonify(job.to_dict()), 200


@app.route("/api/scan/file", methods=["POST"])
def get_file() -> tuple[Response, int]:
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
def review() -> tuple[Response, int]:
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
