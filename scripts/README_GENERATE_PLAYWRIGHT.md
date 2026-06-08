Generate Playwright Java tests from AI test-cases

Overview
--------
This script converts plain-text AI-generated test cases into a Java file containing Playwright + JUnit tests.

Usage
-----
1. Save your AI-generated test cases to a text file, e.g. `testcases.txt`.
2. Run the script and point `--target` to your Playwright Java project root (absolute path):

```bash
python scripts/generate_playwright_java_tests.py \
  --testcases-file ./testcases.txt \
  --issue-key MBA-8 \
  --target /absolute/path/to/agentic-ai-automation-test
```

Output
------
- Creates a Java class under `<target>/src/test/java/ai/generated/GeneratedTests_<issue>_<ts>.java`.
- Each parsed test case becomes a placeholder `@Test` method with step comments.

Post-processing
---------------
The generated tests are placeholders. Open the generated Java file and:
- Replace `page.navigate("about:blank")` with real navigation and actions.
- Add selectors and assertions appropriate for your application.
- Adjust Playwright launch options as needed (headless vs headed).

Notes
-----
- The script doesn't run Maven/Gradle; run your normal test runner in the Playwright Java project after reviewing the generated code.
- The script requires Python 3.8+ and writes files to the target project — ensure you have write access.
