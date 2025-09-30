import json
import logging
import re
import shutil
import subprocess
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from bson import ObjectId
from models.models import JobStatus
import os
from datetime import datetime, timezone, timedelta

import git

logging.basicConfig(level=logging.INFO)


class Scanner:
    def __init__(self, config, mongo):
        self.config = config
        self.mongo = mongo
        self.logger = logging.getLogger(__name__)
        self.semgrep_rules_dir: Path = Path(self.config["paths"]["semgrep_rules_dir"])
        self.clone_base_dir: Path = Path(self.config["paths"]["clone_base_dir"])
        self.exclude_langs = (
            set(self.config["settings"]["exclude_langs"])
            if "exclude_langs" in config["settings"]
            else {}
        )
        self.suppress_paths: List[str] = self.config["settings"].get(
            "suppress_paths", []
        )
        self.suppress_rules: List[str] = self.config["settings"].get(
            "suppress_rules", []
        )

    def run_scan_job(self, job_id: ObjectId, repo_url: str) -> None:
        """
        Runs the scan in a separate thread and updates job status.
        """

        self.mongo.update_job_status(job_id, JobStatus.RUNNING)

        try:
            # Clone the repo
            repo_path: Path = self.clone_repo(repo_url)
            # Run semgrep (writing output to file as before)
            output: str = self.run_semgrep(repo_path)
            cleaned_output: Dict[str, Any] = self.clean_sarif(json.loads(output))

            repo_file_path: str = repo_path.name
            repo_name: str = f"{repo_url.split("/")[-2]}/{repo_url.split("/")[-1]}"

            self.mongo.add_scan_result_to_db(repo_name, cleaned_output)

            self.write_sarif_to_file(cleaned_output, repo_file_path)

            # Delete if no findings
            self.delete_repo_if_no_findings(repo_path, output)

            # Mark job done
            self.mongo.update_job_status(job_id, JobStatus.DONE)
            self.logger.info(f"Scan complete for {repo_name}")

        except Exception as e:
            self.mongo.update_job_on_error(job_id, str(e))
            self.logger.error(f"Scan failed for {repo_name} with error {e}")

    def clone_repo(self, repo_url: str) -> Path:
        # Use last two parts of repo for folder name (e.g., github.com/rs/cors -> rs_cors)
        parts = repo_url.rstrip("/").split("/")[-2:]
        safe_name = "_".join(re.sub(r"[^a-zA-Z0-9_\-]", "_", p) for p in parts)
        clone_dir = self.clone_base_dir / safe_name

        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        git.Repo.clone_from(repo_url, str(clone_dir))
        return clone_dir

    def detect_languages(self, target_dir: Path) -> List[str]:
        """
        Detect languages in the repo using SCC and skip excluded languages.
        """
        cmd = ["scc", "-f", "json", str(target_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"SCC failed: {result.stderr}")

        data = json.loads(result.stdout)
        langs = {
            entry["Name"] for entry in data if entry["Name"] not in self.exclude_langs
        }
        return list(langs)

    def run_semgrep(
        self,
        target_dir: Path,
        exclude_globs: Optional[List[str]] = None,
    ) -> str:
        """
        Run semgrep on the target directory using all detected languages that have rules.
        Runs a single semgrep command with multiple -f flags.
        """
        languages = self.detect_languages(target_dir)
        languages = [lang.lower() for lang in languages]

        valid_rule_dirs = []

        for lang in languages:
            rule_dir = self.semgrep_rules_dir / lang

            if rule_dir.is_dir():
                valid_rule_dirs.append(rule_dir)

        if not valid_rule_dirs:
            self.logger.info("No valid rule directories found.")
            return ""

        # Build semgrep command
        cmd: List[str] = ["semgrep"]
        for rule_dir in valid_rule_dirs:
            cmd.extend(["-f", str(rule_dir)])

        if exclude_globs:
            for g in exclude_globs:
                cmd.extend(["--exclude", g])

        cmd.extend(["--sarif"])
        cmd.append(str(target_dir))

        self.logger.info(f"Running semgrep with command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            self.logger.info(f"Error running semgrep: {result.stderr}")
            return ""

        return result.stdout

    def mark_sarif_suppressed_by_fingerprint(
        self, scan_id: str, fingerprint_id: str, suppress: bool = True
    ) -> Dict[str, Any]:
        sarif = self.mongo.get_sarif_by_id(scan_id)
        if not sarif:
            raise ValueError(f"SARIF not found for scan ID {scan_id}")

        # Update matching results
        for run in sarif.get("runs", []):
            for result in run.get("results", []):
                fingerprints = result.get("fingerprints", {})
                if fingerprints.get("paladin") == fingerprint_id:
                    result["suppressed"] = suppress

        self.mongo.update_scan_by_id(scan_id, sarif)

        return sarif

    def delete_repo_if_no_findings(self, repo_dir: Path, semgrep_output: str) -> None:
        """
        Delete the repo directory if Semgrep found no issues.
        """
        if not semgrep_output.strip():
            shutil.rmtree(repo_dir)
            self.logger.info(f"Deleted {repo_dir} (no findings)")
        else:
            self.logger.info(f"Findings detected in {repo_dir}, keeping repo.")

    def clean_sarif(self, sarif_data_parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans a SARIF JSON object by removing results and rules that match
        suppressed paths or explicit rule IDs from the config.
        """

        rules_path_prefix = (
            ".".join(self.semgrep_rules_dir.parts[1:])
            if self.semgrep_rules_dir.is_absolute()
            else ".".join(self.semgrep_rules_dir.parts)
        )

        for run in sarif_data_parsed.get("runs", []):
            # Clean results
            results: List[Dict[str, Any]] = run.get("results", [])
            cleaned_results: List[Dict[str, Any]] = []

            for result in results:
                rule_id: str = result.get("ruleId", "")

                # Remove rules_path prefix if present
                rule_id_short = (
                    rule_id[len(rules_path_prefix) + 1 :]
                    if rule_id.startswith(rules_path_prefix + ".")
                    else rule_id
                )

                # Suppress if any suppress_path substring is in rule_id_short OR rule_id_short is in suppress_rules
                if (
                    not any(path in rule_id_short for path in self.suppress_paths)
                    and rule_id_short not in self.suppress_rules
                ):
                    result["ruleId"] = rule_id_short
                    # add custom fingerprint
                    result["fingerprints"] = {
                        "paladin": self.generate_fingerprint(result)
                    }
                    cleaned_results.append(result)

            run["results"] = cleaned_results

            # Clean tool.driver.rules
            tool = run.get("tool", {})
            driver = tool.get("driver", {})
            rules: List[Dict[str, Any]] = driver.get("rules", [])
            cleaned_rules: List[Dict[str, Any]] = []

            for rule in rules:
                rule_id: str = rule.get("id", "")
                rule_id_short = (
                    rule_id[len(rules_path_prefix) + 1 :]
                    if rule_id.startswith(rules_path_prefix + ".")
                    else rule_id
                )

                if (
                    not any(path in rule_id_short for path in self.suppress_paths)
                    and rule_id_short not in self.suppress_rules
                ):
                    rule["id"] = rule_id_short
                    cleaned_rules.append(rule)

            driver["rules"] = cleaned_rules
            tool["driver"] = driver
            run["tool"] = tool

        return sarif_data_parsed

    def generate_fingerprint(self, result: Dict[str, Any]) -> str:
        rule_id = result.get("ruleId", "")
        locations = result.get("locations", [])
        snippet_texts = []

        for loc in locations:
            snippet = (
                loc.get("physicalLocation", {})
                .get("region", {})
                .get("snippet", {})
                .get("text", "")
            )
            if snippet:
                snippet_texts.append(snippet.strip())

        # Concatenate ruleId + snippets for hashing
        fingerprint_source = rule_id + "|" + "|".join(snippet_texts)
        fingerprint_hash = hashlib.sha256(
            fingerprint_source.encode("utf-8")
        ).hexdigest()[
            :16
        ]  # short hash
        return fingerprint_hash

    def write_sarif_to_file(self, sarif: Dict[str, Any], repo: str) -> None:
        write_json: bool = self.config.get("settings", {}).get("write_sarif_to_file", None)  # type: ignore
        if not write_json:
            return

        sarif_write_dir: str = self.config.get("paths", {}).get("sarif_write_dir", "")  # type: ignore
        if not sarif_write_dir:
            sarif_write_path: Path = Path(".")
        else:
            sarif_write_path: Path = Path(sarif_write_dir)
            os.makedirs(sarif_write_path, exist_ok=True)

        timestamp: int = int(datetime.now(timezone.utc).timestamp())

        sarif_write_path = sarif_write_path / f"{repo}_{timestamp}.json"
        with open(sarif_write_path, "w+") as f:
            json.dump(sarif, f, indent=4)

        self.logger.info(f"Output written to {sarif_write_path}")

    def should_suppress_findings(self) -> bool:
        settings = self.config.get("settings", {})
        return not settings.get("suppress_paths") or not settings.get("suppress_rules")
