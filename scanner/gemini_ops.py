import logging
from typing import Any, Optional

from google import genai

from models.data_models import FindingForReview
from models.response_models import GeminiReview, ReviewError, ReviewResponse

logging.basicConfig(level=logging.INFO)


class GeminiOps:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def review(
        self,
        finding: FindingForReview,
        joern_trace: Optional[list[dict[str, Any]]],
        file: Optional[list[str]],
    ) -> ReviewResponse:
        prompt = f"""
            You are a security code analysis assistant. You will be given:
            1. A Semgrep finding (rule ID, explanation, and code line).
            2. The joern trace where the finding was reported OR
               The file with the finding


            Your task:
            - Decide if the finding is a TRUE positive (real issue) or a FALSE positive.
            - Use the joern trace or file as context to support your decision.

            Your response will be a json of the format 
            {{
                "verdict" : TRUE OR FALSE,
                "reason" : a short response explaning the verdict
            }}

            ---
            Finding:
            Rule ID: {finding.rule_id}
            Explanation: {finding.description}
            Code line: {finding.snippet}

            Joern Trace:
            {joern_trace}

            File:
            {file}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": GeminiReview,
                },
            )
            if response and response.text:
                return ReviewResponse(None, review=response.parsed)  # type: ignore
            else:
                return ReviewResponse(ReviewError.NO_ANSWER, None)
        except Exception as e:
            raise RuntimeError(f"Gemini request failed with error {e}")
