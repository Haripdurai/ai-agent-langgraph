from flask import Flask, request, jsonify
import os
import requests
import urllib3
from datetime import datetime
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable SSL warnings (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)


def get_issue_summary_and_description(issue_key: str):
    """Fetch summary and description for an issue from Jira Cloud REST API v3."""
    logger.info(f"📥 Fetching issue {issue_key} from Jira...")
    jira_base = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    username = os.environ.get("JIRA_USERNAME", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    if not jira_base or not username or not api_token:
        logger.error("❌ Missing Jira credentials")
        return None, None, "Missing Jira credentials in environment"

    auth = (username, api_token)
    url = f"{jira_base}/rest/api/3/issue/{issue_key}?fields=summary,description"
    try:
        resp = requests.get(url, auth=auth, verify=False)
        logger.info(f"📥 Jira response: {resp.status_code}")
        if resp.status_code != 200:
            return None, None, f"Jira API returned {resp.status_code}: {resp.text}"
        data = resp.json()
        fields = data.get("fields", {})
        summary = fields.get("summary", "(no summary)")
        description = fields.get("description")
        if description is None:
            description_text = "(no description)"
        elif isinstance(description, dict):
            # rough fallback for ADF: stringify
            description_text = str(description)
        else:
            description_text = str(description)
        return summary, description_text, None
    except Exception as e:
        return None, None, str(e)


def load_test_cases_prompt():
    prompts_dir = os.path.join(os.getcwd(), "prompts")
    prompt_file = os.path.join(prompts_dir, "test_cases_prompt.md")
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, "r") as f:
                prompt_content = f.read()
            # Use the part before "## Issue Details" if present
            return prompt_content.split("## Issue Details")[0].strip()
        except Exception:
            pass

    # fallback prompt
    return (
        "You are a senior QA engineer specializing in test case design.\n"
        "Generate comprehensive test cases for the given feature/issue.\n\n"
        "Test Case Categories:\n"
        "1. Positive Test Cases: happy path\n"
        "2. Negative Test Cases: invalid inputs and failures\n"
        "3. Edge Case Test Cases: boundaries and corner cases\n\n"
        "For each test case include ID, Title, Preconditions, Steps, Expected Result, Priority.\n"
        "Return only the test cases – no introduction or closing text."
    )


def generate_test_cases_via_openai(issue_key: str, summary: str, description: str):
    logger.info(f"🤖 Generating test cases via OpenAI for {issue_key}...")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY not set")
        return None, "OPENAI_API_KEY not set in environment"

    system_prompt = load_test_cases_prompt()
    user_message = f"Issue Key: {issue_key}\n\nSummary: {summary}\n\nDescription:\n{description}"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.15,
        "max_tokens": 1500,
    }

    try:
        logger.info("🤖 Calling OpenAI API (this may take 10-30 seconds)...")
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
            verify=False,  # Disable SSL verification for corporate proxy
        )
        logger.info(f"🤖 OpenAI response: {resp.status_code}")
        if resp.status_code != 200:
            logger.error(f"❌ OpenAI error: {resp.text}")
            return None, f"OpenAI API error {resp.status_code}: {resp.text}"
        data = resp.json()
        # extract assistant content
        choices = data.get("choices", [])
        if not choices:
            return None, "No choices returned from OpenAI"
        message = choices[0].get("message", {})
        content = message.get("content") or message.get("message") or ""
        if isinstance(content, dict):
            # some APIs return nested structure
            content = content.get("content", "")
        logger.info(f"✅ Test cases generated ({len(content)} chars)")
        return content.strip(), None
    except Exception as e:
        logger.error(f"❌ OpenAI exception: {e}")
        return None, str(e)


def build_adf_comment(issue_key: str, test_cases_text: str) -> dict:
    return {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Test Cases Generated By AI", "marks": [{"type": "strong"}]}]},
                {"type": "paragraph", "content": [{"type": "text", "text": f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}]} ,
                {"type": "rule"},
                {"type": "codeBlock", "attrs": {"language": "text"}, "content": [{"type": "text", "text": test_cases_text}]}
            ]
        }
    }


@app.route("/jira/generate_and_post", methods=["POST"])
def generate_and_post():
    """Generate test cases for a Jira issue and optionally post them as a comment.

    JSON body: {
      "issue_key": "PROJ-1",
      "post_to_jira": true,    # default true
      "dry_run": true          # default true (if true, do not actually POST to Jira)
    }
    """
    body = request.get_json(force=True)
    issue_key = body.get("issue_key")
    post_to_jira = body.get("post_to_jira", True)
    dry_run = body.get("dry_run", True)

    logger.info(f"🚀 Received request for issue: {issue_key} (post_to_jira={post_to_jira}, dry_run={dry_run})")

    if not issue_key:
        return jsonify({"error": "issue_key is required"}), 400

    # Fetch issue
    summary, description, err = get_issue_summary_and_description(issue_key)
    if err:
        return jsonify({"error": f"Failed to fetch issue: {err}"}), 500

    # Generate test cases
    test_cases, gen_err = generate_test_cases_via_openai(issue_key, summary, description)
    if gen_err:
        return jsonify({"error": f"Failed to generate test cases: {gen_err}"}), 500

    response_payload = {"issue_key": issue_key, "summary": summary, "test_cases": test_cases}

    if post_to_jira:
        jira_base = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
        jira_user = os.environ.get("JIRA_USERNAME")
        jira_token = os.environ.get("JIRA_API_TOKEN")
        if not jira_base or not jira_user or not jira_token:
            return jsonify({"error": "Missing Jira environment variables for posting"}), 500

        jira_url = f"{jira_base}/rest/api/3/issue/{issue_key}/comment"
        adf_payload = build_adf_comment(issue_key, test_cases)

        if dry_run:
            response_payload.update({"dry_run": True, "jira_url": jira_url, "adf_payload": adf_payload})
            return jsonify(response_payload)

        try:
            resp = requests.post(jira_url, json=adf_payload, auth=(jira_user, jira_token), headers={"Content-Type": "application/json"}, verify=False)
            if resp.status_code in (200, 201):
                response_payload.update({"posted": True, "jira_response": resp.json()})
                return jsonify(response_payload), 201
            else:
                response_payload.update({"posted": False, "status_code": resp.status_code, "response_text": resp.text})
                return jsonify(response_payload), resp.status_code
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify(response_payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
