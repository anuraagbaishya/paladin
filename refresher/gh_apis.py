import os
from datetime import datetime, timedelta, timezone
import requests
from typing import Dict, Any, Optional, List
import logging
from models.models import RepoInfo

logging.basicConfig(level=logging.INFO)


class GhApis:
    def __init__(self, token) -> None:
        self.github_token = token
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
        }
        self.github_graphql_api = "https://api.github.com/graphql"
        self.logger = logging.getLogger(__name__)

    def query_recent_ghsa(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        self.logger.info("Querying GitHub REST API for GHSA advisories")
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        all_advisories: List[Dict[str, Any]] = []
        per_page = 100

        url = f"https://api.github.com/advisories?per_page={per_page}"

        while url:
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                advisories = response.json()

                if not advisories:
                    break

                # Loop through advisories in order; stop when older than "since"
                for adv in advisories:
                    published_at = adv.get("published_at")
                    if not published_at:
                        continue

                    if published_at < since:
                        return all_advisories

                    all_advisories.append(adv)

                # If less than page size returned, we are done
                if len(advisories) < per_page:
                    break

                if len(advisories) < per_page:
                    break

                link = response.headers.get("Link", "")
                next_url = None
                for part in link.split(","):
                    if 'rel="next"' in part:
                        next_url = part[part.find("<") + 1 : part.find(">")]
                        break
                url = next_url

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to fetch REST API response: {e}")
                return None

        self.logger.info(f"Fetched {len(all_advisories)} advisories from REST API")
        return all_advisories

    def query_repo_info(self, ecosystem: str, repo: str) -> RepoInfo:
        self.logger.info(f"Querying repo info from Github API for {ecosystem}:{repo}")

        owner, repo = repo.split("/")[0], repo.split("/")[1]
        query = """
        query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            stargazerCount
            forkCount
        }
        }
        """
        try:
            variables = {"owner": owner, "name": repo}
            data = self._query_github_graphql(query, variables)
            repo_info = data.get("data", {}).get("repository")

            if repo_info:
                return RepoInfo(
                    repo=f"{owner}/{repo}",
                    stars=repo_info["stargazerCount"],
                    forks=repo_info["forkCount"],
                )
        except requests.RequestException:
            self.logger.error(f"Failed to fetch repo data for {owner}/{repo}")

        return RepoInfo(repo="", stars=0, forks=0)

    def _query_github_graphql(
        self, query: str, variables: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        r = requests.post(
            "https://api.github.com/graphql",
            headers=self.headers,
            json={"query": query, "variables": variables},
            timeout=15,
        )
        r.raise_for_status()

        return r.json()
