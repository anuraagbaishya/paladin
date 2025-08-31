import json
import logging
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any, Dict, List, Optional

import git

config_path = Path("config.toml")

with config_path.open("rb") as f:
    config = tomllib.load(f)

SEMREGEP_RULES_DIR: Path = Path(config["paths"]["semgrep_rules_dir"])
CLONE_BASE_DIR: Path = Path(config["paths"]["clone_base_dir"])
EXCLUDE_LANGS = (
    set(config["settings"]["exclude_langs"])
    if "exclude_langs" in config["settings"]
    else {}
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def clone_repo(repo_url: str) -> Path:
    # Use last two parts of repo for folder name (e.g., github.com/rs/cors -> rs_cors)
    parts = repo_url.rstrip("/").split("/")[-2:]
    safe_name = "_".join(re.sub(r"[^a-zA-Z0-9_\-]", "_", p) for p in parts)
    clone_dir = CLONE_BASE_DIR / safe_name

    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    git.Repo.clone_from(repo_url, str(clone_dir))
    return clone_dir


def detect_languages(target_dir: Path) -> List[str]:
    """
    Detect languages in the repo using SCC and skip excluded languages.
    """
    cmd = ["scc", "-f", "json", str(target_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"SCC failed: {result.stderr}")

    data = json.loads(result.stdout)
    langs = {entry["Name"] for entry in data if entry["Name"] not in EXCLUDE_LANGS}
    return list(langs)


def run_semgrep(
    target_dir: Path,
    exclude_globs: Optional[List[str]] = None,
) -> str:
    """
    Run semgrep on the target directory using all detected languages that have rules.
    Runs a single semgrep command with multiple -f flags.
    """
    languages = detect_languages(target_dir)
    languages = [lang.lower() for lang in languages]

    valid_rule_dirs = []

    for lang in languages:
        rule_dir = SEMREGEP_RULES_DIR / lang

        if rule_dir.is_dir():
            valid_rule_dirs.append(rule_dir)

    if not valid_rule_dirs:
        logger.info("No valid rule directories found.")
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

    logger.info(f"Running semgrep with command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        logger.info(f"Error running semgrep: {result.stderr}")
        return ""

    return result.stdout


def delete_repo_if_no_findings(repo_dir: Path, semgrep_output: str) -> None:
    """
    Delete the repo directory if Semgrep found no issues.
    """
    if not semgrep_output.strip():
        shutil.rmtree(repo_dir)
        logger.info(f"Deleted {repo_dir} (no findings)")
    else:
        logger.info(f"Findings detected in {repo_dir}, keeping repo.")


def clean_sarif(sarif_data_parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans a SARIF JSON object by removing results and rules that match
    suppressed paths or explicit rule IDs from the config.
    """

    suppress_paths: List[str] = config["settings"].get("suppress_paths", [])
    suppress_rules: List[str] = config["settings"].get("suppress_rules", [])

    rules_path: Path = Path(config["paths"]["semgrep_rules_dir"])
    rules_path_prefix = (
        ".".join(rules_path.parts[1:])
        if rules_path.is_absolute()
        else ".".join(rules_path.parts)
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
                not any(path in rule_id_short for path in suppress_paths)
                and rule_id_short not in suppress_rules
            ):
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
                not any(path in rule_id_short for path in suppress_paths)
                and rule_id_short not in suppress_rules
            ):
                cleaned_rules.append(rule)

        driver["rules"] = cleaned_rules
        tool["driver"] = driver
        run["tool"] = tool

    return sarif_data_parsed


def should_suppress_findings() -> bool:
    global config

    settings = config.get("settings", {})
    return not settings.get("suppress_paths") or not settings.get("suppress_rules")
