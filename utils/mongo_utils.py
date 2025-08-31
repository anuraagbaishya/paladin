from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import unquote

from bson import ObjectId
from pymongo import MongoClient

from models.models import Job, JobStatus, ScanResult


class MongoUtils:
    def __init__(self, config: Dict[str, Any]):
        self.mongo_path: str = config["mongo"]["mongo_path"]
        self.client: MongoClient = MongoClient(f"mongodb://{self.mongo_path}")
        self.db = self.client.go_vuln_db
        self.vuln_reports = self.db.vuln_reports
        self.scan_metadata = self.db.scan_metadata
        self.jobs_collection = self.db.scan_jobs
        self.scan_result_collection = self.db.scan_results

    def get_reports_by_pkg(self):
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
            {
                "$project": {
                    "_id": 0,
                    "repo": "$_id.repo",
                    "pkg": "$_id.pkg",
                    "findings": 1,
                }
            },
            {"$sort": {"repo": 1}},
        ]
        return list(self.vuln_reports.aggregate(pipeline))

    def add_scan_result_to_db(self, repo: str, sarif: Dict[str, Any]):
        scan_result = ScanResult(
            repo=repo,
            scan_result=sarif,
        )

        self.scan_result_collection.insert_one(asdict(scan_result))

    def get_scans_from_db(self, repo: str):
        repo = unquote(repo)

        results = self.scan_result_collection.find({"repo": repo}).to_list()
        for r in results:
            r["_id"] = str(r["_id"])
            sarif = r.get("scan_result", None)
            if not sarif:
                continue

            findings_count = len(sarif["runs"][0]["results"])
            r["findings_count"] = findings_count
            del r["scan_result"]

        return results

    def get_sarif_by_id(self, id: str) -> Dict[str, Any]:
        sarif = self.scan_result_collection.find_one({"_id": ObjectId(id)})
        return sarif["scan_result"]  # type: ignore

    def add_job_to_db(self, repo_url: str) -> Job:
        job = Job(repo_url)

        job_as_dict = asdict(job)
        job_as_dict["status"] = job_as_dict["status"].value
        job_as_dict.pop("_id", None)

        result = self.jobs_collection.insert_one(job_as_dict)
        job._id = result.inserted_id
        return job

    def update_job_status(self, job_id: ObjectId, status: JobStatus) -> None:
        self.jobs_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": status.value,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    def update_job_on_error(self, job_id: ObjectId, error: str):
        self.jobs_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": JobStatus.ERROR.value,
                    "error": error,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        res = self.jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not res:
            return None

        res["status"] = JobStatus(res["status"])
        return Job(**res)
