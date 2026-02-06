from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import unquote
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient
from pymongo.results import DeleteResult
from pysarif import SarifLog

from models.data_models import ScanResult, VulnReport
from models.enums import JobStatus
from models.response_models import GeminiReview, JobResponse
from utils.config import Config


class MongoUtils:
    def __init__(self, config: Config):
        self.client: MongoClient = MongoClient(config.mongo_host, config.mongo_port)
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

    def insert_scan_result(self, repo: str, sarif: SarifLog):
        rule_to_severity: dict[str, str] | None = self.rule_to_severity(sarif)
        scan_id = str(uuid4())

        for run in sarif.runs:
            if not run.results:
                continue

            for result in run.results:
                if not result or not result.rule_id:
                    continue

                if not rule_to_severity:
                    severity: str = "unknown"
                else:
                    severity = rule_to_severity[result.rule_id] or "unknown"

                scan_result = ScanResult(
                    scan_id=scan_id,
                    repo=repo,
                    result=result,
                    severity=severity.lower(),
                )

                self.scan_result_collection.insert_one(scan_result.model_dump())

    def rule_to_severity(self, sarif: SarifLog) -> dict[str, str] | None:
        rule_to_severity = {}

        runs = sarif.runs
        if not runs:
            return None

        for run in runs:
            rules = run.tool.driver.rules
            if not rules:
                continue

            for rule in rules:
                rule_to_severity[rule.id] = (
                    rule.default_configuration.level
                    if rule.default_configuration
                    else None
                )

        return rule_to_severity

    def get_scans_by_repo(self, repo: str):
        repo = unquote(repo)

        pipeline = [
            {"$match": {"repo": repo}},
            {
                "$group": {
                    "_id": "$scan_id",
                    "timestamp": {"$first": "$timestamp"},
                    "findings_count": {"$sum": 1},
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "scan_id": "$_id",
                    "timestamp": 1,
                    "findings_count": 1,
                }
            },
            {"$sort": {"timestamp": -1}},
        ]

        return list(self.scan_result_collection.aggregate(pipeline))

    def get_result_by_fingerprint(
        self, scan_id: str, fingerprint: str
    ) -> ScanResult | None:
        result = self.scan_result_collection.find_one(
            {"result.fingerprint.paladin": fingerprint, "scan_id": scan_id}
        )
        if not result:
            return None

        return ScanResult(**result)

    def update_suppression_by_fingerprint(
        self, scan_id: str, fingerprint: str, suppressed: bool
    ):
        self.scan_result_collection.update_one(
            {"scan_id": str(scan_id), "result.fingerprint.paladin": fingerprint},
            {"$set": {"suppressed": suppressed}},
        )

    def update_ai_review_by_scan_id(
        self, scan_id: str, fingerprint: str, ai_review: GeminiReview
    ):
        self.scan_result_collection.update_one(
            {"scan_id": str(scan_id), "result.fingerprint.paladin": fingerprint},
            {"$set": {"ai_review": ai_review.model_dump()}},
        )

    def get_scan_by_id(self, scan_id: str) -> ScanResult | None:
        scan = self.scan_result_collection.find_one(
            {"scan_id": str(scan_id)}, {"_id": 0}
        )
        if scan:
            return ScanResult(**scan)
        else:
            return None

    def get_results_by_scan_id(self, scan_id: str) -> list[ScanResult]:
        results = self.scan_result_collection.find(
            {"scan_id": str(scan_id)}, {"_id": 0}
        ).to_list()
        return [ScanResult(**r) for r in results]

    def delete_scan_by_id(self, id: str) -> bool:
        result: DeleteResult = self.scan_result_collection.delete_one(
            {"_id": ObjectId(id)}
        )
        return result.deleted_count > 0

    def update_result_by_id(
        self, scan_id: str, fingerprint: str, result: ScanResult
    ) -> None:
        self.scan_result_collection.update_one(
            {"scan_id": scan_id, "result.fingerprint.paladin": fingerprint},
            {"$set": {"result": result.result}},
        )

    def add_job_to_db(self, job: JobResponse) -> ObjectId:
        job_dict: Dict[str, Any] = job.to_dict()
        job_dict.pop("_id")

        result = self.jobs_collection.insert_one(job_dict)

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
            {"$set": report.model_dump()},
            upsert=True,
        )
