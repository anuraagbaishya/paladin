import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pysarif import Location, Result, SarifLog, save_to_file


class SarifUtils:
    def __init__(
        self,
        semgrep_rules_dir: Path,
        suppress_paths: List[str],
        suppress_rules: List[str],
        sarif_write_dir: Optional[Path] = None,
        write_sarif_to_file: bool = False,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.semgrep_rules_dir = semgrep_rules_dir
        self.suppress_paths = suppress_paths
        self.suppress_rules = suppress_rules
        self.sarif_write_dir = sarif_write_dir
        self.write_sarif_to_file_enabled = write_sarif_to_file

    def clean_sarif(self, sarif: SarifLog) -> SarifLog:
        """Clean and filter SARIF results based on suppression rules."""
        rules_path_prefix = (
            ".".join(self.semgrep_rules_dir.parts[1:])
            if self.semgrep_rules_dir.is_absolute()
            else ".".join(self.semgrep_rules_dir.parts)
        )

        for run in sarif.runs:
            results: List[Result] | None = run.results
            cleaned_results: List[Result] = []

            if not results:
                continue

            for result in results:
                rule_id: str | None = result.rule_id

                if not rule_id:
                    continue

                # Remove rules_path prefix if present
                rule_id_short = (
                    rule_id[len(rules_path_prefix) + 1 :]
                    if rule_id.startswith(rules_path_prefix + ".")
                    else rule_id
                )

                # Suppress if any suppress_path substring is in rule_id_short OR rule_id_short is in suppress_rules
                if (
                    any(path in rule_id_short for path in self.suppress_paths)
                    or rule_id_short in self.suppress_rules
                ):
                    continue

                result.rule_id = rule_id_short
                # add custom fingerprint
                if not result.fingerprints:
                    result.fingerprints = {}
                result.fingerprints["paladin"] = self.generate_fingerprint(result)
                cleaned_results.append(result)

            run.results = cleaned_results

            # Clean tool.driver.rules
            if not (run.tool and run.tool.driver and run.tool.driver.rules):
                continue

            cleaned_rules = []
            for rule in run.tool.driver.rules:
                rule_id = rule.id if hasattr(rule, "id") else ""
                rule_id_short = (
                    rule_id[len(rules_path_prefix) + 1 :]
                    if rule_id.startswith(rules_path_prefix + ".")
                    else rule_id
                )

                if (
                    any(path in rule_id_short for path in self.suppress_paths)
                    and rule_id_short in self.suppress_rules
                ):
                    continue

                if hasattr(rule, "id"):
                    rule.id = rule_id_short
                cleaned_rules.append(rule)

            run.tool.driver.rules = cleaned_rules

        return sarif

    def generate_fingerprint(self, result: Result) -> str | None:
        """Generate a unique fingerprint for a SARIF result."""
        rule_id: str | None = result.rule_id
        locations: list[Location] | None = result.locations
        snippet_texts = []

        if not locations:
            return None

        for loc in locations:
            try:
                if not loc.physical_location:
                    continue

                region = loc.physical_location.region
                if not region or not region.snippet:
                    continue

                snippet = region.snippet.text
                if not snippet:
                    continue

                snippet_texts.append(snippet.strip())

            except (AttributeError, TypeError) as e:
                self.logger.error(f"Fingerprint generation failed: {e}")

        # Concatenate ruleId + snippets for hashing
        fingerprint_source = (rule_id or "") + "|" + "|".join(snippet_texts)
        fingerprint_hash = hashlib.sha256(
            fingerprint_source.encode("utf-8")
        ).hexdigest()

        return fingerprint_hash

    def write_sarif_to_file(self, sarif: SarifLog, repo: str) -> None:
        """Write SARIF results to a JSON file."""
        if not self.write_sarif_to_file_enabled:
            return

        if not self.sarif_write_dir:
            sarif_write_path: Path = Path(".")
        else:
            sarif_write_path: Path = Path(self.sarif_write_dir)
            os.makedirs(sarif_write_path, exist_ok=True)

        timestamp: int = int(datetime.now(timezone.utc).timestamp())

        sarif_write_path = sarif_write_path / f"{repo}_{timestamp}.json"
        save_to_file(sarif, str(sarif_write_path))

        self.logger.info(f"Output written to {sarif_write_path}")

    def get_finding_by_fingerprint(
        self, sarif: Dict[str, Any], fingerprint_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find a specific result in SARIF by its fingerprint."""
        # there should be only 1 finding per fingerprint
        # if that is not the case, fix the fingerprint function
        for run in sarif.get("runs", []):
            for result in run.get("results", {}):
                fingerprints = result.get("fingerprints", {})
                if fingerprints.get("paladin") == fingerprint_id:
                    return result

        return None

    def validate_location(self, location: Location | None) -> bool:
        """Validate that a location has all required fields."""
        if not location:
            return False

        if not location.physical_location:
            return False

        if not location.physical_location.artifact_location:
            return False

        if not location.physical_location.artifact_location.uri:
            return False

        if not location.physical_location.region:
            return False

        if not location.physical_location.region.snippet:
            return False

        if not location.physical_location.region.snippet.text:
            return False

        return True
