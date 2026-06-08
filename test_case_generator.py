import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import requests
import base64
import urllib3
import httpx
from datetime import datetime

# ===== DISABLE SSL VERIFICATION GLOBALLY =====
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Read credentials from environment variables
JIRA_INSTANCE_URL = os.environ.get("JIRA_INSTANCE_URL", "https://haridurai1230.atlassian.net").rstrip("/")
JIRA_USERNAME     = os.environ.get("JIRA_USERNAME", "haridurai1230@gmail.com")
JIRA_API_TOKEN    = os.environ.get("JIRA_API_TOKEN", "")
GROK_API_KEY      = os.environ.get("GROK_API_KEY", "")

logger.info("Environment variables loaded")
logger.info(f"  JIRA URL: {JIRA_INSTANCE_URL}")
logger.info(f"  JIRA User: {JIRA_USERNAME}")
logger.info(f"  JIRA Token: {'✓ set' if JIRA_API_TOKEN else '✗ missing'}")
logger.info(f"  GROK Key:  {'✓ set' if GROK_API_KEY else '✗ missing'}")

if not JIRA_API_TOKEN:
    logger.warning("⚠️  JIRA_API_TOKEN not found in .env")
if not GROK_API_KEY:
    logger.warning("⚠️  GROK_API_KEY not found in .env")

# ===== Initialize LLM (Grok API with SSL verification disabled) =====
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Custom httpx client that skips SSL verification (corporate proxy fix)
http_client = httpx.Client(verify=False)

llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    temperature=0.15,
    openai_api_key=GROK_API_KEY,
    openai_api_base="https://api.groq.com/openai/v1",
    http_client=http_client,
)

logger.info("✓ LLM initialized: openai/gpt-oss-120b via Groq API")

# ===== Load prompt =====
# Try multiple locations for the prompt file
prompt_file = None
search_paths = [
    Path.cwd() / "prompts" / "test_cases_prompt.md",
    Path(__file__).parent / "prompts" / "test_cases_prompt.md",
]

for p in search_paths:
    if p.exists():
        prompt_file = p
        break

if prompt_file:
    with open(prompt_file, "r") as f:
        prompt_content = f.read()
    test_cases_prompt_text = prompt_content.split("## Issue Details")[0].strip()
    logger.info(f"✓ Test Cases Prompt loaded from {prompt_file}")
else:
    logger.warning("⚠️  Prompt file not found, using embedded default")
    test_cases_prompt_text = (
        "You are a senior QA engineer specializing in test case design.\n"
        "Generate comprehensive test cases for the given feature/issue.\n\n"
        "Test Case Categories:\n"
        "1. **Positive Test Cases**: Test happy path scenarios where everything works as expected.\n"
        "2. **Negative Test Cases**: Test error scenarios, invalid inputs, and failure conditions.\n"
        "3. **Edge Case Test Cases**: Test boundary conditions, limits, and corner cases.\n\n"
        "For each test case, include:\n"
        "- Test Case ID (e.g., TC001, TC002)\n"
        "- Title: Brief description\n"
        "- Preconditions: What must be true before executing\n"
        "- Steps: Numbered action steps\n"
        "- Expected Result: What should happen\n"
        "- Priority: High/Medium/Low\n\n"
        "Format each test case clearly with sections separated by dashes.\n"
        "Aim for 3-5 positive cases, 3-5 negative cases, and 2-4 edge cases based on complexity.\n"
        "Return only the test cases – no introduction or closing text."
    )

# Create the prompt template and chain
TEST_CASES_PROMPT = ChatPromptTemplate.from_messages([
    ("system", test_cases_prompt_text),
    ("human", "Issue Key: {key}\n\nSummary: {summary}\n\nDescription:\n{description}")
])

test_cases_chain = TEST_CASES_PROMPT | llm

# ===== Jira helper functions =====

def _get_jira_auth() -> tuple:
    """Return (username, api_token) tuple for requests auth."""
    return (JIRA_USERNAME, JIRA_API_TOKEN)

def _get_jira_headers() -> dict:
    """Create Jira request headers."""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def _extract_adf_text(adf: dict) -> str:
    """Recursively extract plain text from Atlassian Document Format."""
    if not isinstance(adf, dict):
        return str(adf) if adf else ""

    texts = []

    def _walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                _walk(child)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(adf)
    return "\n".join(texts)

def get_issue_summary_and_description(issue_key: str) -> dict:
    """Fetch issue from Jira Cloud. Tries v2, then v3."""
    logger.info(f"🔍 Fetching Jira issue: {issue_key}")

    headers = _get_jira_headers()
    auth = _get_jira_auth()

    # v2 returns description as plain text; v3 returns it as ADF
    urls = [
        f"{JIRA_INSTANCE_URL}/rest/api/2/issue/{issue_key}",
        f"{JIRA_INSTANCE_URL}/rest/api/3/issue/{issue_key}",
    ]

    last_error = None
    for url in urls:
        logger.info(f"  📡 Trying: {url}")
        try:
            response = requests.get(
                url, headers=headers, auth=auth, verify=False, timeout=15
            )
            logger.info(f"  Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                summary = data.get("fields", {}).get("summary", "")
                description_raw = data.get("fields", {}).get("description", "") or ""

                # If description is ADF (dict), extract plain text
                if isinstance(description_raw, dict):
                    description = _extract_adf_text(description_raw)
                else:
                    description = description_raw

                logger.info(f"  ✓ Issue fetched: {summary}")
                logger.info(f"    Description: {len(description)} chars")
                return {"summary": summary, "description": description}
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"  ✗ {last_error}")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"  ✗ Failed: {e}")

    raise Exception(f"Could not fetch issue {issue_key} from Jira. Last error: {last_error}")

def post_test_cases_to_jira(issue_key: str, test_cases: str) -> dict:
    """Post test cases as a formatted comment to Jira issue."""
    logger.info(f"📤 Posting test cases to Jira issue: {issue_key}")

    headers = _get_jira_headers()
    auth = _get_jira_auth()

    comment_data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Test Cases Generated By AI",
                            "marks": [{"type": "strong"}]
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                },
                {
                    "type": "rule"
                },
                {
                    "type": "codeBlock",
                    "attrs": {"language": "text"},
                    "content": [
                        {
                            "type": "text",
                            "text": test_cases
                        }
                    ]
                }
            ]
        }
    }

    url = f"{JIRA_INSTANCE_URL}/rest/api/3/issue/{issue_key}/comment"
    logger.info(f"  📡 POST {url}")

    response = requests.post(
        url, json=comment_data, headers=headers, auth=auth,
        verify=False, timeout=30,
    )

    if response.status_code == 201:
        comment_id = response.json().get("id", "")
        logger.info(f"  ✓ Comment posted (ID: {comment_id})")
        return {"status": "success", "comment_id": comment_id}
    else:
        error_msg = f"HTTP {response.status_code}: {response.text[:300]}"
        logger.error(f"  ✗ Failed to post comment: {error_msg}")
        return {"status": "failed", "error": error_msg}

# ===== Main function =====

def generate_test_cases_for_issue(issue_key: str) -> dict:
    """
    End-to-end: Fetch Jira issue → generate test cases via LLM → post back to Jira.
    """
    logger.info("=" * 70)
    logger.info(f"🚀 Starting test case generation for: {issue_key}")
    logger.info("=" * 70)

    # Step 1: Fetch Jira issue
    logger.info("STEP 1: Fetching Jira issue details...")
    info = get_issue_summary_and_description(issue_key)
    logger.info(f"  Summary: {info['summary']}")

    # Step 2: Generate test cases via LLM
    logger.info("STEP 2: Calling LLM (openai/gpt-oss-120b via Grok)...")
    result = test_cases_chain.invoke({
        "key": issue_key,
        "summary": info["summary"],
        "description": info["description"]
    })
    test_cases = result.content.strip()
    logger.info(f"  ✓ LLM returned {len(test_cases)} chars")

    # Step 3: Post to Jira
    logger.info("STEP 3: Posting test cases to Jira as comment...")
    post_result = post_test_cases_to_jira(issue_key, test_cases)

    logger.info("=" * 70)
    logger.info(f"✅ COMPLETE — Jira comment: {post_result.get('status')}")
    logger.info("=" * 70)

    return {
        "issue_key": issue_key,
        "summary": info["summary"],
        "description": info["description"],
        "test_cases": test_cases,
    }