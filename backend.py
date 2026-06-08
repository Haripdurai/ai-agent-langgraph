from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import logging
import traceback

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

# ===== Models =====

class TestCaseRequest(BaseModel):
    issue_key: str

class TestCaseResponse(BaseModel):
    issue_key: str
    summary: str
    description: str
    test_cases: str

# ===== Path to React build =====
BUILD_DIR = Path(__file__).parent / "test-case-generator-ui" / "build"

# ===== API Routes =====

@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

@app.post("/api/generate-test-cases", response_model=TestCaseResponse, tags=["Generate"])
async def generate_test_cases(request: TestCaseRequest):
    """
    Analyse a Jira ticket, generate test cases via LLM, and publish
    the test cases back to the Jira ticket as a comment.
    """
    logger.info(f"POST /api/generate-test-cases  issue_key={request.issue_key}")

    try:
        from test_case_generator import generate_test_cases_for_issue

        result = generate_test_cases_for_issue(request.issue_key)
        logger.info(f"✅ Done for {request.issue_key}")
        return TestCaseResponse(**result)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# ===== Serve React static files =====
# Mount static assets (JS, CSS, images)
if BUILD_DIR.exists():
    app.mount("/static", StaticFiles(directory=BUILD_DIR / "static"), name="static")

    # Catch-all: serve index.html for any non-API route (React client-side routing)
    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        # If the requested file exists in build dir, serve it (e.g. manifest.json, favicon)
        file_path = BUILD_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(BUILD_DIR / "index.html")
else:
    logger.warning(f"⚠️  React build not found at {BUILD_DIR}. Run 'npm run build' in test-case-generator-ui/")

    @app.get("/")
    async def root():
        return {"message": "React build not found. Run 'npm run build' in test-case-generator-ui/"}

# ===== Entrypoint =====

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)