API to post generated test cases to Jira

Quick start

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt
```

2. Set environment variables (example):

```bash
export JIRA_INSTANCE_URL="https://yourcompany.atlassian.net"
export JIRA_USERNAME="your.email@example.com"
export JIRA_API_TOKEN="your_api_token"
```

3. Run the API:

```bash
python api/app.py
```

4. Example dry-run request using `curl`:

```bash
curl -X POST http://localhost:5000/jira/comments/testcases \
  -H "Content-Type: application/json" \
  -d '{"issue_key":"PROJ-1","test_cases":"TC001 - ...","dry_run":true}'
```

5. To actually post the comment, set `"dry_run": false` in the JSON payload.

Notes

- The API uses basic auth with `JIRA_USERNAME` and `JIRA_API_TOKEN` from environment variables.
- The comment is created using Atlassian Document Format (ADF) and places the generated test cases inside a `codeBlock` so formatting is preserved.
- For production, run behind a WSGI server (gunicorn/uvicorn) and secure the endpoint (authentication, TLS, etc.).
