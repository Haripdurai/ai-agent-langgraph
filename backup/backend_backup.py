from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from test_case_generator import generate_test_cases_for_issue
import logging
import traceback
import os
from dotenv import load_dotenv
import requests
import base64

# Load env vars first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(title="Test Case Generator API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define models
class TestCaseRequest(BaseModel):
    issue_key: str

class TestCaseResponse(BaseModel):
    issue_key: str
    summary: str
    description: str
    test_cases: str

# Routes
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Test Case Generator API",
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

@app.get("/test-jira-api/{issue_key}", tags=["Debug"])
async def test_jira_api(issue_key: str):
    """Test Jira API directly to debug issue fetching."""
    logger.info(f"Testing Jira API for issue: {issue_key}")
    
    try:
        jira_url = os.environ.get("JIRA_INSTANCE_URL", "").rstrip("/")
        username = os.environ.get("JIRA_USERNAME", "")
        api_token = os.environ.get("JIRA_API_TOKEN", "")
        
        if not jira_url or not username or not api_token:
            return {
                "status": "error",
                "message": "Missing Jira credentials"
            }
        
        # Create auth header
        credentials = f"{username}:{api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json"
        }
        
        # Try API v3 first (Cloud)
        url_v3 = f"{jira_url}/rest/api/3/issues/{issue_key}"
        logger.info(f"Trying API v3: {url_v3}")
        
        response_v3 = requests.get(
            url_v3,
            headers=headers,
            verify=False,
            timeout=10
        )
        
        if response_v3.status_code == 200:
            data = response_v3.json()
            return {
                "status": "success",
                "api_version": "v3",
                "url": url_v3,
                "summary": data.get("fields", {}).get("summary", ""),
                "description": data.get("fields", {}).get("description", "")
            }
        
        # Try API v2 (older versions)
        url_v2 = f"{jira_url}/rest/api/2/issue/{issue_key}"
        logger.info(f"Trying API v2: {url_v2}")
        
        response_v2 = requests.get(
            url_v2,
            headers=headers,
            verify=False,
            timeout=10
        )
        
        if response_v2.status_code == 200:
            data = response_v2.json()
            return {
                "status": "success",
                "api_version": "v2",
                "url": url_v2,
                "summary": data.get("fields", {}).get("summary", ""),
                "description": data.get("fields", {}).get("description", "")
            }
        
        # Both failed
        return {
            "status": "error",
            "message": f"Issue {issue_key} not found",
            "tried_urls": [url_v3, url_v2],
            "v3_status": response_v3.status_code,
            "v3_response": response_v3.text[:500],
            "v2_status": response_v2.status_code,
            "v2_response": response_v2.text[:500]
        }
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/generate-test-cases", response_model=TestCaseResponse, tags=["Generate"])
async def generate_test_cases(request: TestCaseRequest):
    """Generate test cases for a Jira issue."""
    logger.info(f"Generating test cases for: {request.issue_key}")
    
    try:
        result = generate_test_cases_for_issue(request.issue_key)
        logger.info(f"✅ Test cases generated for {request.issue_key}")
        return TestCaseResponse(**result)
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# Run
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)