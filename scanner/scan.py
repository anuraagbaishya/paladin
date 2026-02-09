import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import git
from bson import ObjectId
from pysarif import Run, SarifLog, load_from_file
import requests

from models.data_models import FindingForReview, ScanMetadata, ScanResult
from models.enums import JobStatus
from models.response_models import (
    ClaudeResponse,
    FileError,
    FileResponse,
    ReviewError,
    ReviewResponse,
)
from utils.config import Config
from utils.mongo_utils import MongoUtils

from .sarif_utils import SarifUtils

logging.basicConfig(level=logging.INFO)


class Scanner:
    def __init__(self, config: Config, mongo: MongoUtils) -> None:
        self.config = config
        self.mongo = mongo
        self.logger = logging.getLogger(__name__)

        self.sarif_utils = SarifUtils(
            semgrep_rules_dir=self.config.semgrep_rules_dir,
            suppress_paths=self.config.suppress_paths,
            suppress_rules=self.config.suppress_rules,
            sarif_write_dir=self.config.sarif_write_dir,
        )

        if not self.config.clone_base_dir.exists():
            os.makedirs(self.config.clone_base_dir, exist_ok=True)

    def run_scan_job(self, job_id: ObjectId, repo_url: str) -> None:
        self.mongo.update_job_status(job_id, JobStatus.RUNNING)
        repo_name: str = f"{repo_url.split('/')[-2]}/{repo_url.split('/')[-1]}"

        try:
            repo_path: Path = self.clone_repo(repo_url)
            languages: List[str] = self.detect_languages(repo_path)
            output: SarifLog | None = self.run_semgrep(repo_path, languages)

            if not output:
                self.mongo.update_job_status(
                    job_id, JobStatus.ERROR, "no sarif produced"
                )
                self.logger.error(
                    f"Scan failed for {repo_name} with error no sarif produced"
                )
                return

            cleaned_sarif: SarifLog = self.sarif_utils.clean_sarif(output)
            repo_file_path: str = repo_path.name

            scan_id: str = self.mongo.insert_scan_result(cleaned_sarif)
            self.sarif_utils.write_sarif_to_file(cleaned_sarif, repo_file_path)

            findings_count = sum(
                len(run.results or []) for run in cleaned_sarif.runs or []
            )
            metadata = ScanMetadata(
                scan_id=scan_id,
                repo=repo_name,
                languages=languages,
                findings_count=findings_count,
            )
            self.mongo.insert_scan_metadata(metadata)

            # Delete if no findings
            self.delete_repo_if_no_findings(repo_path, cleaned_sarif)

            # Mark job done
            self.mongo.update_job_status(job_id, JobStatus.DONE)
            self.logger.info(f"Scan complete for {repo_name}")

        except Exception as e:
            self.mongo.update_job_status(job_id, JobStatus.ERROR, str(e))
            self.logger.error(f"Scan failed for {repo_name} with error {e}")

    def mark_sarif_suppressed_by_fingerprint(
        self, scan_id: str, fingerprint: str, suppress: bool = True
    ) -> None:
        self.mongo.update_suppression_by_fingerprint(scan_id, fingerprint, suppress)

    def get_file(self, filepath: str) -> FileResponse:
        base_path = Path(self.config.clone_base_dir).resolve()
        requested_path = Path(filepath).resolve()

        # Ensure requested_path is inside base_path
        try:
            if os.path.commonpath([str(base_path), str(requested_path)]) != str(
                base_path
            ):
                self.logger.error(f"Invalid path {filepath}")
                return FileResponse(FileError.INVALID_PATH, None)
        except ValueError:
            self.logger.error(f"Invalid path {filepath}")
            return FileResponse(FileError.INVALID_PATH, None)

        if not requested_path.is_file():
            self.logger.error(f"File not found {filepath}")
            return FileResponse(FileError.NOT_FOUND, None)

        try:
            with requested_path.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return FileResponse(None, lines)
        except Exception as e:
            self.logger.error(f"Failed to read {filepath}: {e}")
            return FileResponse(FileError.READ_FAIL)

    def review(self, scan_id: str, fingerprint_id: str) -> ReviewResponse:
        repo: str | None = self.mongo.get_repo_by_scan_id(scan_id)
        if not repo:
            return ReviewResponse(error=ReviewError.NO_FINDING)

        repo_path = str(self.config.clone_base_dir / repo)

        scan_result: ScanResult | None = self.mongo.get_result_by_fingerprint(
            scan_id, fingerprint_id
        )
        if not scan_result:
            return ReviewResponse(error=ReviewError.NO_FINDING)

        if not scan_result.file or not scan_result.snippet:
            return ReviewResponse(error=ReviewError.INCOMPLETE_FINDING)

        finding_for_review: FindingForReview = FindingForReview(
            repo=repo_path, scan_result=scan_result
        )

        try:
            claude_response: Optional[ClaudeResponse] = self.claude_code_assessment(
                finding_for_review
            )

            if not claude_response:
                self.logger.error("Claude assessment failed: no response received")
                return ReviewResponse(error=ReviewError.REVIEW_FAIL)

            if not claude_response.review:
                self.logger.error(
                    f"Claude response failed, no review received: {claude_response.error}"
                )
                return ReviewResponse(error=ReviewError.REVIEW_FAIL)

            self.mongo.update_ai_review_by_scan_id(
                scan_id, fingerprint_id, claude_response.review
            )

            return ReviewResponse(review=claude_response.review)
        except RuntimeError as e:
            self.logger.error(f"Claude review failed: {e}")
            return ReviewResponse(error=ReviewError.REVIEW_FAIL)

    def clone_repo(self, repo_url: str, clone_base_dir: Optional[Path] = None) -> Path:
        # Use last two parts of repo for folder name (e.g., github.com/rs/cors -> rs/cors)
        parts = repo_url.rstrip("/").split("/")[-2:]
        safe_name = "/".join(re.sub(r"[^a-zA-Z0-9_\-]", "_", p) for p in parts)
        if not clone_base_dir:
            clone_base_dir = self.config.clone_base_dir

        clone_dir = clone_base_dir / safe_name

        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        self.logger.info(f"Cloning repo {repo_url}")
        git.Repo.clone_from(repo_url, str(clone_dir))
        return clone_dir

    def detect_languages(self, target_dir: Path) -> List[str]:
        cmd = ["scc", "-f", "json", str(target_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"SCC failed: {result.stderr}")

        data = json.loads(result.stdout)
        langs: set[str] = {
            entry["Name"]
            for entry in data
            if entry["Name"].lower() not in self.config.exclude_langs
        }

        return list(langs)

    def run_semgrep(
        self,
        target_dir: Path,
        languages: list[str],
        exclude_globs: Optional[List[str]] = None,
    ) -> SarifLog | None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=True) as tmp:
            tmp_path = tmp.name

            languages = [lang.lower() for lang in languages]

            valid_rule_dirs = []

            for lang in languages:
                rule_dir = self.config.semgrep_rules_dir / lang

                if rule_dir.is_dir():
                    valid_rule_dirs.append(rule_dir)

            if not valid_rule_dirs:
                self.logger.info("No valid rule directories found.")
                return None

            cmd: List[str] = ["semgrep"]
            for rule_dir in valid_rule_dirs:
                cmd.extend(["-f", str(rule_dir)])

            if exclude_globs:
                for g in exclude_globs:
                    cmd.extend(["--exclude", g])

            cmd.extend(["--sarif", "-o", tmp_path, str(target_dir)])

            self.logger.info(f"Running semgrep with command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode not in (0, 1):
                self.logger.info(f"Error running semgrep: {result.stderr}")
                return None

            return load_from_file(tmp_path)

    def delete_repo_if_no_findings(self, repo_dir: Path, sarif: SarifLog) -> None:
        runs: List[Run] | None = sarif.runs
        if not runs:
            shutil.rmtree(repo_dir)
            self.logger.info(f"Deleted {repo_dir} (no findings)")
            return

        results = sarif.runs[0].results

        if not results:
            shutil.rmtree(repo_dir)
            self.logger.info(f"Deleted {repo_dir} (no findings)")
        else:
            self.logger.info(f"Findings detected in {repo_dir}, keeping repo.")

    def claude_code_assessment(
        self, finding_for_review: FindingForReview
    ) -> Optional[ClaudeResponse]:
        self.logger.info(f"Reviewing {finding_for_review.model_dump()}")
        # bridge server runs on host
        bridge_server_url = os.getenv("CLAUDE_BRIDGE_URL", "")
        if not bridge_server_url:
            return None

        response = requests.post(
            f"{bridge_server_url}/review", json=finding_for_review.model_dump()
        )
        if response and response.json():
            self.logger.info(f"Claude response: {response.json()}")
            return ClaudeResponse.model_validate(response.json())

        return None
