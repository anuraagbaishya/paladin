import os
from datetime import datetime, timedelta, timezone
from utils.mongo_utils import MongoUtils
import logging
from .gh_apis import GhApis
from models.models import RepoInfo, VulnReport, Cwe
from typing import Optional, Dict, Any, List
from .cwe_import import CweImport

logging.basicConfig(level=logging.INFO)


class Refresher:
    def __init__(self, mongo: MongoUtils) -> None:
        self.mongo = mongo
        self.gh_apis = GhApis()
        self.logger = logging.getLogger(__name__)
        self.cwe_import = CweImport()

    def refresh(self, days: int = 7) -> None:
        if not self.mongo.do_cwes_exist():
            cwes: Optional[List[Cwe]] = self.cwe_import.import_cwes()
            if cwes:
                for cwe in cwes:
                    self.mongo.add_cwe_to_db(cwe)

        vulns: Optional[List[Dict[str, Any]]] = self.gh_apis.query_recent_ghsa(days)
        if not vulns:
            self.logger.info("No GHSAs queried")
            return None

        self.logger.info(f"Queried {len(vulns)} GHSAs")

        total_vulns = len(vulns)
        count = 0
        for vuln in vulns:
            count += 1
            ghsa = vuln.get("ghsaId")
            self.logger.debug(f"Processing {count}/{total_vulns}: {ghsa}")

            seen = set()
            vuln_nodes = vuln.get("vulnerabilities", {}).get("nodes", [])
            for vuln_node in vuln_nodes:
                pkg: str = vuln_node["package"]["name"]
                ecosystem: str = vuln_node["package"]["ecosystem"].lower()
                if pkg in seen:
                    continue
                seen.add(pkg)

                report: VulnReport = self._process_package(vuln, ecosystem, pkg)
                self.mongo.upsert_vuln_report_to_db(report)

        self.logger.info(f"Upserted {count} GHSA entries into MongoDB")

    def _process_package(self, advisory, ecosystem, pkg) -> VulnReport:
        cwes: List[Dict[str, Any]] = advisory.get("cwes", {}).get("nodes", [])
        cwe_id: Optional[int] = int(cwes[0]["cweId"].split("CWE-")[1]) if cwes else None
        cwe_title: Optional[str] = self.mongo.get_cwe_title(cwe_id) if cwe_id else None

        cve: Optional[str] = next(
            (i["value"] for i in advisory.get("identifiers", []) if i["type"] == "CVE"),
            None,
        )
        severity: str = advisory.get("severity")
        cvss: Dict[str, Any] = advisory.get("cvss", {})
        cvss_score: Optional[float] = cvss.get("score")
        cvss_vector: Optional[str] = cvss.get("vectorString")

        repo_info: RepoInfo = self.gh_apis.query_repo_info(ecosystem, pkg)

        repo: Optional[str] = repo_info.repo if repo_info.repo else None
        stars: Optional[int] = repo_info.stars if repo_info.stars else None
        forks: Optional[int] = repo_info.forks if repo_info.forks else None

        return VulnReport(
            package=pkg,
            repo=repo,
            ecosystem=ecosystem,
            title=advisory["summary"],
            ghsa=advisory["ghsaId"],
            cve=cve,
            stars=stars,
            forks=forks,
            severity=severity,
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            cwe=Cwe(cwe_id, cwe_title) if (cwe_id and cwe_title) else None,
        )
