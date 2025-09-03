import os
from datetime import datetime, timedelta, timezone
import requests
from typing import Dict, Any, Optional, List
import logging
from .repo_guesser import RepoGuesser
from models.models import RepoInfo

logging.basicConfig(level=logging.INFO)


class GhApis:
    def __init__(self) -> None:
        self.github_token = os.getenv("GH_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
        }
        self.github_graphql_api = "https://api.github.com/graphql"
        self.logger = logging.getLogger(__name__)
        self.repo_guesser = RepoGuesser()

    def query_recent_ghsa(self, days: int = 7) -> Optional[List[Dict[str, Any]]]:
        self.logger.info("Querying Github API for GHSA")
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = """
        query($since: DateTime!, $cursor: String) {
        securityAdvisories(first: 50, publishedSince: $since, after: $cursor, orderBy: {field: PUBLISHED_AT, direction: DESC}) {
            pageInfo {
            hasNextPage
            endCursor
            }
            nodes {
            ghsaId
            summary
            severity
            identifiers { type value }
            cvss { score vectorString }
            cwes(first: 5) { nodes { cweId description } }
            vulnerabilities(first: 10) { nodes { package { ecosystem name } } }
            publishedAt
            }
        }
        }
        """

        all_advisories = []
        cursor = None

        while True:
            variables = {"since": since, "cursor": cursor}
            try:
                data = self._query_github_graphql(query, variables)
                if not "data" in data:
                    return None

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to fetch API response: {e}")

            advisories = data.get("data", {}).get("securityAdvisories", {})
            nodes = advisories.get("nodes", [])
            all_advisories.extend(nodes)

            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        self.logger.info(len(all_advisories))
        return all_advisories

    def query_repo_info(self, ecosystem: str, pkg_name: str) -> RepoInfo:
        self.logger.info(
            f"Querying repo info from Github API for {ecosystem}:{pkg_name}"
        )
        candidates = self.repo_guesser.guess_github_repo_candidates(ecosystem, pkg_name)

        if not candidates:
            return RepoInfo(repo="", stars=0, forks=0)

        for owner, repo_candidate in candidates:
            query = """
            query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                stargazerCount
                forkCount
            }
            }
            """
            try:
                variables = {"owner": owner, "name": repo_candidate}
                data = self._query_github_graphql(query, variables)
                repo_info = data.get("data", {}).get("repository")

                if data:
                    return RepoInfo(
                        repo=f"{owner}/{repo_candidate}",
                        stars=repo_info["stargazerCount"],
                        forks=repo_info["forkCount"],
                    )
            except requests.RequestException:
                self.logger.error(
                    f"Failed to fetch repo data for {owner}/{repo_candidate}"
                )
                continue
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
