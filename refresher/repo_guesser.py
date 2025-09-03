from typing import List, Optional, Tuple, Dict, Any, NamedTuple
import requests


class Repo(NamedTuple):
    owner: str
    repo: str


class RepoGuesser:
    def __init__(self) -> None:
        pass

    def guess_github_repo_candidates(
        self, ecosystem: str, pkg_name: str
    ) -> Optional[List[Repo]]:
        if ecosystem == "go":
            return self._guess_go_repo_from_pkg(pkg_name)
        elif ecosystem == "pypi" or ecosystem == "pip":
            return self._guess_pypi_repo_from_pkg(pkg_name)
        elif ecosystem == "npm":
            return self._guess_npm_repo_from_pkg(pkg_name)
        elif ecosystem == "composer":
            return self._guess_composer_repo_from_pkg(pkg_name)
        else:
            return None

    def _guess_pypi_repo_from_pkg(self, pkg: str) -> Optional[List[Repo]]:
        url = f"https://pypi.org/pypi/{pkg}/json"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json().get("info", {})

            # Prefer "Source Code" from project_urls
            project_urls = data.get("project_urls", {})
            repo_url = project_urls.get("Source Code")

            # Fallback: try "home_page"
            if not repo_url:
                repo_url = data.get("home_page")

            # fallback 2: try project_urls.Homepage
            if not repo_url:
                repo_url = project_urls.get("Homepage")

            # Only return GitHub repos
            if repo_url:
                repo_url = repo_url.replace("git+", "").replace(".git", "")
                return self._extract_owner_repo_from_url(repo_url.rstrip("/"))
        except requests.RequestException:
            pass

        return None

    def _guess_composer_repo_from_pkg(self, pkg: str) -> Optional[List[Repo]]:
        """Get GitHub repo from Packagist (Composer)"""
        url = f"https://repo.packagist.org/p2/{pkg}.json"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            # Grab repository from latest package version

            versions = data.get("packages", {}).get(pkg, [])

            if versions:
                repo_url = versions[0].get("source", {}).get("url")

                if repo_url:
                    repo_url = repo_url.replace("git+", "").replace(".git", "")
                    return self._extract_owner_repo_from_url(repo_url.rstrip("/"))
        except requests.RequestException:
            pass
        return None

    def _guess_npm_repo_from_pkg(self, pkg) -> Optional[List[Repo]]:
        url = f"https://registry.npmjs.org/{pkg}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            repo_url = data.get("repository", {}).get("url")

            if not repo_url:
                repo_url = data.get("homepage")

            if repo_url:
                repo_url = repo_url.replace("git+", "").replace(".git", "")
                return self._extract_owner_repo_from_url(repo_url.rstrip("/"))

        except requests.RequestException:
            pass
        return None

    def _guess_go_repo_from_pkg(self, pkg) -> Optional[List[Repo]]:
        if not pkg.startswith("github.com/"):
            return []
        path = pkg[len("github.com/") :]
        parts = path.split("/")

        if parts[-1].startswith("v") and parts[-1][1:].isdigit():
            parts = parts[:-1]
        if len(parts) < 2:
            return []

        owner = parts[0]

        candidate1 = "/".join(parts[1:])
        candidate2 = parts[1] if parts[1] != candidate1 else None

        candidates = [candidate1]
        if candidate2:
            candidates.append(candidate2)
        return [Repo(owner, repo) for repo in candidates]

    def _extract_owner_repo_from_url(self, url: str) -> List[Repo]:
        parts = url.split("/")
        owner = parts[-2]
        repo = parts[-1]

        return [Repo(owner, repo)]

    def _make_request(self, url: str) -> Dict[str, Any]:
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        return r.json()
