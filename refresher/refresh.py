import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId

from models.data_models import Cwe, RepoInfo, VulnReport
from models.enums import JobStatus
from utils.mongo_utils import MongoUtils

from .gh_apis import GhApis

logging.basicConfig(level=logging.INFO)


class Refresher:
    def __init__(self, token: str, mongo: MongoUtils) -> None:
        self.mongo = mongo
        self.logger = logging.getLogger(__name__)
        self.token = token
        self.gh_apis = GhApis(token)

    def refresh(self, job_id: ObjectId, days: int = 7) -> None:
        self.logger.info(f"Querying GHSAs for last {days} days")
        self.mongo.update_job_status(job_id, JobStatus.RUNNING)

        ghsas: Optional[List[Dict[str, Any]]] = self.gh_apis.query_recent_ghsa(days)
        if not ghsas:
            self.logger.info("No GHSAs queried")
            self.mongo.update_job_status(job_id, JobStatus.DONE)
            return None

        self.logger.info(f"Queried {len(ghsas)} GHSAs")

        count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for ghsa in ghsas:
                count += 1
                seen: Set[str] = set()

                vulns: List[Dict[str, Any]] = ghsa.get("vulnerabilities", [])
                for vuln in vulns:
                    futures.append(
                        executor.submit(self._process_vuln_node, ghsa, vuln, seen)
                    )

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Error processing vulnerability: {e}")

            self.logger.info(f"Upserted {count} GHSA entries into MongoDB")
            self.mongo.update_job_status(job_id, JobStatus.DONE)

    def _process_vuln_node(
        self, ghsa: Dict[str, Any], vuln_node: Dict[str, Any], seen: Set[str]
    ):
        pkg: str = vuln_node["package"]["name"]
        ecosystem: str = vuln_node["package"]["ecosystem"].lower()
        repo_url: str = ghsa.get("source_code_location", "")
        repo: Optional[str] = None

        if repo_url:
            repo = repo_url.replace("https://github.com/", "")

        if pkg in seen:
            return

        seen.add(pkg)

        report: VulnReport = self._process_package(ghsa, ecosystem, pkg, repo)
        self.mongo.upsert_vuln_report_to_db(report)

    def _process_package(
        self, advisory: Dict[str, Any], ecosystem: str, pkg: str, repo: Optional[str]
    ) -> VulnReport:
        cwes: List[Dict[str, Any]] = advisory.get("cwes", [])

        cwe_id: Optional[str] = None
        cwe_title: Optional[str] = None

        if cwes:
            cwe_id = cwes[0]["cwe_id"] if cwes else None
            cwe_title = cwes[0]["name"] if cwes else None

        cve: Optional[str] = next(
            (i["value"] for i in advisory.get("identifiers", []) if i["type"] == "CVE"),
            None,
        )
        severity: str = advisory.get("severity", {})
        cvss: Optional[Dict[str, Any]] = self._get_cvss_score(
            advisory.get("cvss_severities", {})
        )
        if cvss:
            cvss_score: Optional[float] = cvss.get("score")
            cvss_vector: Optional[str] = cvss.get("vectorString")

        stars: Optional[int] = None
        forks: Optional[int] = None

        if repo:
            repo_info: RepoInfo = self.gh_apis.query_repo_info(ecosystem, repo)

            stars = repo_info.stars if repo_info.stars else None
            forks = repo_info.forks if repo_info.forks else None

        return VulnReport(
            package=pkg,
            repo=repo,
            ecosystem=ecosystem,
            title=advisory["summary"],
            ghsa=advisory["ghsa_id"],
            cve=cve,
            stars=stars,
            forks=forks,
            severity=severity,
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            cwe=Cwe(cwe_id, cwe_title) if (cwe_id and cwe_title) else None,
        )

    def _get_cvss_score(self, cvss: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not cvss:
            return None

        if "cvss_v4" in cvss and cvss.get("cvss_v4", {}).get("score") != 0:
            return cvss["cvss_v4"]

        return cvss["cvss_v3"]
