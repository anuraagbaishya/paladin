import subprocess
from pathlib import Path
from typing import List, Optional
import shutil
import tempfile
import uuid
import git
import json
import re

SEMREGEP_RULES_DIR: Path = Path("/Users/anuraagbaishya/Projects/semgrep-rules")
EXCLUDE_LANGS = {"Dockerfile", "Makefile", "YAML", "JSON"}
CLONE_BASE_DIR = Path("/tmp/repos")


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
        print("No valid rule directories found.")
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

    print(f"Running semgrep with command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        print(f"Error running semgrep: {result.stderr}")
        return ""

    return result.stdout


def delete_repo_if_no_findings(repo_dir: Path, semgrep_output: str) -> None:
    """
    Delete the repo directory if Semgrep found no issues.
    """
    if not semgrep_output.strip():
        shutil.rmtree(repo_dir)
        print(f"Deleted {repo_dir} (no findings)")
    else:
        print(f"Findings detected in {repo_dir}, keeping repo.")
