from flask import Flask, request, jsonify
import subprocess
import json
from bridge_models import AiReview, ClaudeResponse, FindingForReview

app = Flask(__name__)

schema = {
    "type": "object",
    "properties": {
        "verdict": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}


@app.route("/review", methods=["POST"])
def analyze_code():
    data = request.get_json()
    finding = FindingForReview.model_validate(data)

    try:
        prompt = f"Use the semgrep-sarif-triage skill to analyze this finding: {finding.scan_result.model_dump()}"

        cmd = [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema),
            prompt,
        ]

        result: subprocess.CompletedProcess = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=finding.repo,
        )

        if result.returncode != 0:
            return jsonify(ClaudeResponse(error=result.stderr).model_dump()), 500

        jsonified_stdout = json.loads(result.stdout)

        claude_response: ClaudeResponse = ClaudeResponse(
            error=result.stderr,
            review=AiReview.model_validate(jsonified_stdout["structured_output"]),
        )

        return jsonify(claude_response.model_dump())

    except subprocess.TimeoutExpired:
        return jsonify(ClaudeResponse(error="request timed out").model_dump()), 504
    except Exception as e:
        return jsonify(ClaudeResponse(error=str(e)).model_dump()), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
