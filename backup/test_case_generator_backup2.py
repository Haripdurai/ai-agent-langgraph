import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import requests
import base64
import urllib3
import ssl
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
os.environ["JIRA_INSTANCE_URL"] = os.environ.get("JIRA_INSTANCE_URL", "https://haridurai1230.atlassian.net/")
os.environ["JIRA_USERNAME"]     = os.environ.get("JIRA_USERNAME", "haridurai1230@gmail.com")
os.environ["JIRA_API_TOKEN"]    = os.environ.get("JIRA_API_TOKEN", "")
os.environ["JIRA_CLOUD"]        = "true"
os.environ["OPENAI_API_KEY"]    = os.environ.get("OPENAI_API_KEY", "")

logger.info("Environment variables loaded")

if not os.environ.get("JIRA_API_TOKEN"):
    logger.warning("⚠️  JIRA_API_TOKEN not found")
if not os.environ.get("OPENAI_API_KEY"):
    logger.warning("⚠️  OPENAI_API_KEY not found")
else:
    logger.info("✓ All credentials loaded")

# ===== Initialize LLM with SSL verification DISABLED =====
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI

# Create a custom httpx client that skips SSL verification
http_client = httpx.Client(verify=False)

# Create OpenAI client with custom http_client
openai_client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    http_client=http_client
)

# Pass the custom client to ChatOpenAI
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.15,
    client=openai_client.chat.completions,
    openai_api_key=os.environ.get("OPENAI_API_KEY")
)

logger.info("✓ LLM initialized: gpt-4o-mini (SSL verification disabled)")

# ===== Load prompt =====
prompts_dir = Path.cwd() / "prompts"
prompt_file = prompts_dir / "test_cases_prompt.md"

try:
    with open(prompt_file, "r") as f:
        prompt_content = f.read()
    
    test_cases_prompt_text = prompt_content.split("## Issue Details")[0].strip()
    logger.info(f"✓ Test Cases Prompt loaded from {prompt_file}")
except FileNotFoundError:
    logger.warning(f"⚠️  Prompt file not found at {prompt_file}")
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

def _get_jira_headers() -> dict:
    """Create Jira auth headers."""
    username = os.environ.get("JIRA_USERNAME", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")
    credentials = f"{username}:{api_token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def get_issue_summary_and_description(issue_key: str) -> dict:
    """Fetch issue from Jira. Tries v2 and v3 endpoints."""
    logger.info(f"Fetching Jira issue: {issue_key}")
    
    jira_url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    headers = _get_jira_headers()
    
    # Try both API versions
    urls = [
        f"{jira_url}/rest/api/2/issue/{issue_key}",
        f"{jira_url}/rest/api/3/issue/{issue_key}",
    ]
    
    for url in urls:
        logger.info(f"📡 Trying: {url}")
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                summary = data.get("fields", {}).get("summary", "")
                description = data.get("fields", {}).get("description", "") or ""
                
                # Handle ADF format description (Jira Cloud v3)
                if isinstance(description, dict):
                    # Extract text from Atlassian Document Format
                    texts = []
                    for content_block in description.get("content", []):
                        for inner in content_block.get("content", []):
                            if inner.get("type") == "text":
                                texts.append(inner.get("text", ""))
                    description = "\n".join(texts)
                
                logger.info(f"✓ Issue fetched: {summary}")
                logger.info(f"  Description length: {len(description)} chars")
                return {"summary": summary, "description": description}
        except Exception as e:
            logger.warning(f"  Failed: {e}")
            continue
    
    raise Exception(f"Could not fetch issue {issue_key} from Jira")

def post_test_cases_to_jira(issue_key: str, test_cases: str) -> dict:
    """Post test cases as a comment to Jira issue."""
    logger.info(f"Posting test cases to Jira issue: {issue_key}")
    
    jira_url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
    headers = _get_jira_headers()
    
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
    
    url = f"{jira_url}/rest/api/3/issue/{issue_key}/comment"
    logger.info(f"📡 Posting comment to: {url}")
    
    response = requests.post(
        url,
        json=comment_data,
        headers=headers,
        verify=False,
        timeout=15
    )
    
    if response.status_code == 201:
        comment_id = response.json().get("id", "")
        logger.info(f"✓ Comment posted successfully (ID: {comment_id})")
        return {"status": "success", "comment_id": comment_id}
    else:
        logger.error(f"Failed to post comment: {response.status_code} - {response.text}")
        return {"status": "failed", "error": response.text}

# ===== Main function =====

def generate_test_cases_for_issue(issue_key: str) -> dict:
    """Generate test cases for a Jira issue and post to Jira."""
    logger.info("=" * 70)
    logger.info(f"🚀 Starting test case generation for: {issue_key}")
    logger.info("=" * 70)
    
    try:
        # Step 1: Get Jira details
        logger.info("STEP 1: Fetching Jira issue details...")
        info = get_issue_summary_and_description(issue_key)
        
        # Step 2: Generate test cases with LLM
        logger.info("STEP 2: Calling OpenAI LLM to generate test cases...")
        logger.info(f"   Model: gpt-4o-mini | Temperature: 0.15")
        
        result = test_cases_chain.invoke({
            "key": issue_key,
            "summary": info["summary"],
            "description": info["description"]
        })
        
        test_cases = result.content.strip()
        logger.info("✓ LLM generation successful")
        
        # Step 3: Post to Jira as comment
        logger.info("STEP 3: Posting test cases to Jira...")
        post_result = post_test_cases_to_jira(issue_key, test_cases)
        
        logger.info("=" * 70)
        logger.info("✓ COMPLETE: Test case generation finished successfully")
        logger.info("=" * 70)
        
        return {
            "issue_key": issue_key,
            "summary": info["summary"],
            "description": info["description"],
            "test_cases": test_cases
        }
    
    except Exception as e:
        logger.error(f"❌ FAILED: {e}")
        raise Exception(f"Test case generation failed: {e}")