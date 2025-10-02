from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import unquote

from bson import ObjectId
from pymongo import MongoClient
from pymongo.results import DeleteResult

from models.data_models import Cwe, ScanResult, VulnReport
from models.enums import JobStatus
from models.response_models import JobResponse


class MongoUtils:
    def __init__(self, config: Dict[str, Any]):
        self.mongo_path: str = config["mongo"]["mongo_path"]
        self.client: MongoClient = MongoClient(f"mongodb://{self.mongo_path}")
        self.db = self.client.paladin
        self.vuln_reports_collection = self.db.vuln_reports
        self.scan_metadata = self.db.scan_metadata
        self.jobs_collection = self.db.scan_jobs
        self.scan_result_collection = self.db.scan_results
        self.cwe_collection = self.db.cwes

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
                            "ecosystem": "$ecosystem",
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
        return list(self.vuln_reports_collection.aggregate(pipeline))

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

    def delete_scan_by_id(self, id: str) -> bool:
        result: DeleteResult = self.scan_result_collection.delete_one(
            {"_id": ObjectId(id)}
        )
        return result.deleted_count > 0

    def update_scan_by_id(self, id: str, sarif: Dict[str, Any]) -> None:
        self.scan_result_collection.update_one(
            {"_id": ObjectId(id)}, {"$set": {"scan_result": sarif}}
        )

    def add_job_to_db(self, job: JobResponse) -> ObjectId:
        print(job.to_dict())
        result = self.jobs_collection.insert_one(job.to_dict())

        return result.inserted_id

    def update_job_status(
        self, job_id: ObjectId, status: JobStatus, error: Optional[str] = None
    ) -> None:
        self.jobs_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": status.value,
                    "error": error,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    def get_job_by_id(self, job_id: str) -> Optional[JobResponse]:
        res = self.jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not res:
            return None

        res["status"] = JobStatus(res["status"])
        return JobResponse(**res)

    def upsert_vuln_report_to_db(self, report: VulnReport):
        self.vuln_reports_collection.update_one(
            {"ghsa": report.ghsa},
            {"$set": asdict(report)},
            upsert=True,
        )
