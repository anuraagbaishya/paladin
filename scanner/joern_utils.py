import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from cpgqls_client import CPGQLSClient


class JoernUtils:
    def __init__(self, base_repo_path):
        self.server = "localhost:8080"
        self.last_project = None
        self.frontend_map = {
            "python": "PYTHONSRC",
            "javascript": "JAVASCRIPT",
            "typescript": "JAVASCRIPT",
        }
        self.base_repo_path: Path = base_repo_path
        logging.getLogger("pygount").setLevel(logging.WARNING)

    def get_trace(self, repo, finding, language=None) -> list[dict[str, Any]]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            client = CPGQLSClient(self.server)
            repo_name = Path(repo).name.lower()

            loc = finding["locations"][0]["physicalLocation"]
            rel_path = os.path.relpath(
                loc["artifactLocation"]["uri"], self.base_repo_path
            ).replace("\\", "/")

            if not language:
                language = (
                    "python" if rel_path.lower().endswith(".py") else "javascript"
                )

            lang_low = language.lower()
            proj_name = f"{repo_name}_{lang_low}"

            if not self.setup_joern(client, self.base_repo_path, repo_name, lang_low):
                return []

            if self.last_project != proj_name:
                print(f"[*] Switching context: {self.last_project} -> {proj_name}")
                client.execute(f'open("{proj_name}")')
                self.last_project = proj_name

            query_body = self.generate_query_body(
                rel_path, loc["region"].get("snippet", {}).get("text", ""), lang_low
            )
            response = client.execute(query_body)
            return self.process_response(response)
        finally:
            loop.close()

    def setup_joern(self, client, repo_path, repo_name, lang):
        repo_name_low = repo_name.lower()
        proj_name = f"{repo_name_low}_{lang}"
        print(repo_path)

        existing = client.execute("workspace.projects.map(_.name).l").get("stdout", "")
        if proj_name in existing:
            return True

        frontend = self.frontend_map.get(lang)
        if not frontend:
            return False

        print(f"[*] Importing: {proj_name}")
        client.execute(
            f'importCode(inputPath="{repo_path}", projectName="{proj_name}", language="{frontend}")'
        )
        client.execute(f'open("{proj_name}")')
        client.execute("run.ossdataflow")
        self.last_project = proj_name
        return True

    def generate_query_body(self, rel_path, snippet_text, lang):
        clean_snippet = snippet_text.strip().split("\n")[0].replace('"', '\\"')
        print(rel_path)
        try:
            with open(f"scanner/queries/{lang}_query.txt") as f:
                return f.read().format(filename=rel_path, snippet=clean_snippet)
        except FileNotFoundError:
            return 'println("###RESULT###[]###RESULT###")'

    def process_response(self, response) -> list[dict[str, Any]]:
        stdout = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub(
            "", response.get("stdout", "")
        )
        match = re.search(r"###RESULT###(.*?)###RESULT###", stdout, re.DOTALL)
        if match:
            print(match)

            try:
                raw = (
                    match.group(1).strip().encode().decode("unicode_escape").strip('"')
                )
                return [
                    {
                        "joern_context": base64.b64decode(i["sink"]).decode(),
                        "joern_trace": [
                            base64.b64decode(p).decode()
                            for p in i.get("full_trace", [])
                        ],
                    }
                    for i in json.loads(raw)
                ]
            except:
                pass
        return []
