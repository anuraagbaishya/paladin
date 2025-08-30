from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from scanner.scan import clone_repo, run_semgrep, delete_repo_if_no_findings
from uuid import uuid4
from datetime import datetime, timezone
import threading
import tomllib
from pathlib import Path

app = Flask(__name__)

config_path = Path("config.toml")

with config_path.open("rb") as f:
    config = tomllib.load(f)

mongo_path: str = config["mongo"]["mongo_path"]
client = MongoClient(f"mongodb://{mongo_path}")
db = client.go_vuln_db
vuln_reports = db.vuln_reports
scan_metadata = db.scan_metadata
jobs_collection = db.scan_jobs


def get_reports_by_pkg():
    pipeline = [
        {
            "$group": {
                "_id": {"repo": "$repo", "pkg": "$package"},
                "findings": {
                    "$push": {
                        "ghsa": "$ghsa",
                        "cve": "$cve",
                        "cwe": "$cwe",
                        "forks": "$forks",
                        "stars": "$stars",
                        "title": "$title",
                        "cvss_score": "$cvss_score",
                        "cvss_vector": "$cvss_vector",
                        "severity": "$severity",
                    }
                },
            }
        },
        {"$project": {"_id": 0, "repo": "$_id.repo", "pkg": "$_id.pkg", "findings": 1}},
        {"$sort": {"repo": 1}},
    ]
    return list(vuln_reports.aggregate(pipeline))


def run_scan_job(job_id: str, repo_url: str):
    """
    Runs the scan in a separate thread and updates job status.
    """
    jobs_collection.update_one(
        {"job_id": job_id},
        {"$set": {"status": "running", "updated_at": datetime.now(timezone.utc)}},
    )
    try:
        # Clone the repo
        repo_path = clone_repo(repo_url)
        # Run semgrep (writing output to file as before)
        output = run_semgrep(repo_path)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        repo_file_path = repo_path.name

        file_path = f"/tmp/{repo_file_path}_{timestamp}.json"
        with open(file_path, "w") as f:
            f.write(output)
            print(f"Output written to {file_path}")
        # Delete if no findings
        delete_repo_if_no_findings(repo_path, output)

        # Mark job done
        jobs_collection.update_one(
            {"job_id": job_id},
            {"$set": {"status": "done", "updated_at": datetime.now(timezone.utc)}},
        )
    except Exception as e:
        jobs_collection.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "status": "error",
                    "error": str(e),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vuln_reports")
def get_vuln_reports():
    reports = get_reports_by_pkg()
    return jsonify(reports)


@app.route("/scan", methods=["POST"])
def submit_scan():
    data = request.json
    repo = data.get("repo")
    repo_url = f"https://github.com/{repo}"

    if not repo_url:
        return jsonify({"error": "No repo provided"}), 400

    job_id = str(uuid4())
    jobs_collection.insert_one(
        {
            "job_id": job_id,
            "repo": repo_url,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )

    # Run scan in background thread
    threading.Thread(target=run_scan_job, args=(job_id, repo_url), daemon=True).start()

    return jsonify({"job_id": job_id})


@app.route("/scan_status/<job_id>")
def get_scan_status(job_id):
    job = jobs_collection.find_one({"job_id": job_id})
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(
        {"job_id": job["job_id"], "status": job["status"], "error": job.get("error")}
    )


if __name__ == "__main__":
    app.run(debug=True, port=9001)
