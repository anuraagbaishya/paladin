from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import unquote
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient
from pymongo.results import DeleteResult
from pysarif import SarifLog

from models.data_models import ScanMetadata, ScanResult, VulnReport
from models.enums import JobStatus
from models.response_models import AiReview, JobResponse
from utils.config import Config


class MongoUtils:
    def __init__(self, config: Config):
        self.client: MongoClient = MongoClient(config.mongo_host, config.mongo_port)
        self.db = self.client.paladin
        self.vuln_reports_collection = self.db.vuln_reports
        self.scan_metadata = self.db.scan_metadata
        self.jobs = self.db.scan_jobs
        self.scan_result = self.db.scan_results

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

    def insert_scan_result(self, sarif: SarifLog) -> str:
        rule_to_severity: dict[str, str] | None = self.rule_to_severity(sarif)
        scan_id = str(uuid4())

        for run in sarif.runs:
            if not run.results:
                continue

            for result in run.results:
                if not result or not result.rule_id:
                    continue

                loc = result.locations[0] if result.locations else None
                if not loc or not loc.physical_location:
                    continue

                phys = loc.physical_location
                file_uri = (
                    phys.artifact_location.uri if phys.artifact_location else None
                )
                start_line = phys.region.start_line if phys.region else None
                end_line = phys.region.end_line if phys.region else None
                snippet_text = (
                    phys.region.snippet.text or ""
                    if phys.region and phys.region.snippet
                    else ""
                )

                if not file_uri or start_line is None:
                    continue

                fingerprint = (
                    result.fingerprints.get("paladin", "")
                    if result.fingerprints
                    else ""
                )
                description = (result.message.text or "") if result.message else ""

                dataflows = None
                if result.code_flows:
                    dataflows = [cf.to_dict() for cf in result.code_flows]  # type: ignore[union-attr]

                if not rule_to_severity:
                    severity: str = "unknown"
                else:
                    severity = rule_to_severity[result.rule_id] or "unknown"

                scan_result = ScanResult(
                    scan_id=scan_id,
                    fingerprint=fingerprint,
                    file=file_uri,
                    start_line=start_line,
                    end_line=end_line or start_line,
                    rule_id=result.rule_id,
                    snippet=snippet_text,
                    description=description,
                    severity=severity.lower(),
                    dataflows=dataflows,
                )

                self.scan_result.insert_one(scan_result.model_dump())

        return scan_id

    def insert_scan_metadata(self, metadata: ScanMetadata) -> None:
        self.scan_metadata.insert_one(metadata.model_dump())

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

    def get_all_scans(self, limit: int = 200):
        return list(
            self.scan_metadata.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        )

    def get_scans_by_repo(self, repo: str):
        repo = unquote(repo)
        return list(
            self.scan_metadata.find({"repo": repo}, {"_id": 0}).sort("timestamp", -1)
        )

    def get_result_by_fingerprint(
        self, scan_id: str, fingerprint: str
    ) -> ScanResult | None:
        result = self.scan_result.find_one(
            {"fingerprint": fingerprint, "scan_id": scan_id}
        )
        if not result:
            return None

        return ScanResult(**result)

    def update_suppression_by_fingerprint(
        self, scan_id: str, fingerprint: str, suppressed: bool
    ):
        self.scan_result.update_one(
            {"scan_id": str(scan_id), "fingerprint": fingerprint},
            {"$set": {"suppressed": suppressed}},
        )

    def update_ai_review_by_scan_id(
        self, scan_id: str, fingerprint: str, ai_review: AiReview
    ):
        self.scan_result.update_one(
            {"scan_id": str(scan_id), "fingerprint": fingerprint},
            {"$set": {"ai_review": ai_review.model_dump()}},
        )

    def get_scan_by_id(self, scan_id: str) -> ScanResult | None:
        scan = self.scan_result.find_one({"scan_id": str(scan_id)}, {"_id": 0})
        if scan:
            return ScanResult(**scan)
        else:
            return None

    def get_results_by_scan_id(self, scan_id: str) -> list[ScanResult]:
        results = self.scan_result.find(
            {"scan_id": str(scan_id), "suppressed": False}, {"_id": 0}
        ).to_list()
        return [ScanResult(**r) for r in results]

    def delete_scan_by_id(self, scan_id: str) -> bool:
        result: DeleteResult = self.scan_result.delete_many({"scan_id": scan_id})
        result = self.scan_metadata.delete_one({"scan_id": scan_id})
        return result.deleted_count > 0

    def add_job_to_db(self, job: JobResponse) -> ObjectId:
        job_dict: Dict[str, Any] = job.to_dict()
        job_dict.pop("_id")

        result = self.jobs.insert_one(job_dict)

        return result.inserted_id

    def update_job_status(
        self, job_id: ObjectId, status: JobStatus, error: Optional[str] = None
    ) -> None:
        self.jobs.update_one(
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
        res = self.jobs.find_one({"_id": ObjectId(job_id)})
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

    def get_repo_by_scan_id(self, scan_id: str) -> Optional[str]:
        repo = self.scan_metadata.find_one({"scan_id": scan_id}, {"_id": 0, "repo": 1})
        if repo:
            return repo["repo"]

        return None
