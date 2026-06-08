#!/usr/bin/env python3
"""
Generate Java Playwright test files from plain-text AI-generated test cases.

Usage:
  python scripts/generate_playwright_java_tests.py \
    --testcases-file /path/to/testcases.txt \
    --issue-key MBA-8 \
    --target /absolute/path/to/playwright-project

The script creates: <target>/src/test/java/ai/generated/GeneratedTests_<issue>_<ts>.java

Note: The script generates placeholder steps and comments; you should review and refine the generated tests.
"""
import argparse
import os
import re
import datetime


def slugify(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def split_test_cases(text: str):
    # Prefer explicit '---' separators, otherwise split on 'TC' headings
    parts = [p.strip() for p in re.split(r"\n-{3,}\n", text) if p.strip()]
    if len(parts) > 1:
        return parts

    # fallback: split by lines starting with TC<digits>
    matches = re.split(r"(?=TC\d+\s*-)", text)
    return [m.strip() for m in matches if m.strip()]


def extract_title_and_steps(case_text: str):
    # Try to get a title from the first line
    lines = [l.rstrip() for l in case_text.splitlines() if l.strip()]
    title = lines[0] if lines else "Generated Test"

    # Collect Steps: look for a 'Steps:' header then numbered list
    steps = []
    try:
        joined = "\n".join(lines)
        m = re.search(r"Steps:\s*(.*)", joined, flags=re.IGNORECASE | re.DOTALL)
        if m:
            after = m.group(1)
            # split numbered steps
            steps = re.findall(r"\d+\.\s*(.+)", after)
        else:
            # fallback: find lines that look like '1.' or '-' items
            steps = [l for l in lines if re.match(r"^\d+\.", l) or l.startswith("-")]
            steps = [re.sub(r"^\d+\.\s*", "", s).lstrip('- ').strip() for s in steps]
    except Exception:
        steps = []

    return title, steps


TEMPLATE = '''package ai.generated;

import com.microsoft.playwright.*;
import org.junit.jupiter.api.*;

public class {class_name} {{
    private static Playwright pw;
    private static Browser browser;
    private Page page;

    @BeforeAll
    public static void setupAll() {{
        pw = Playwright.create();
        browser = pw.chromium().launch(new BrowserType.LaunchOptions().setHeadless(true));
    }}

    @AfterAll
    public static void tearDownAll() {{
        if (browser != null) browser.close();
        if (pw != null) pw.close();
    }}

    @BeforeEach
    public void setup() {{
        page = browser.newPage();
    }}

    @AfterEach
    public void tearDown() {{
        if (page != null) page.close();
    }}

{test_methods}
}}
'''

METHOD_TEMPLATE = '''    @Test
    public void {method_name}() {{
        // Title: {title}
        // Preconditions: {preconditions}
{steps_comments}
        // TODO: Replace the following placeholder with real actions/assertions
        page.navigate("about:blank");
        Assertions.assertTrue(true);
    }}

'''


def generate_java(class_name: str, tests: list):
    methods = []
    for i, (title, steps) in enumerate(tests, start=1):
        method_name = f"test_{i:03d}_{slugify(title)[:40]}"
        preconditions = "None"
        steps_comments = "\n".join([f"        // Step {idx+1}: {s}" for idx, s in enumerate(steps)]) if steps else "        // Steps: (not parsed)"
        methods.append(METHOD_TEMPLATE.format(method_name=method_name, title=title.replace('"','\"'), preconditions=preconditions, steps_comments=steps_comments))

    return TEMPLATE.format(class_name=class_name, test_methods="".join(methods))


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--testcases-file", required=True)
    parser.add_argument("--issue-key", required=False, default="AI")
    parser.add_argument("--target", required=True, help="Absolute path to Playwright Java project root")
    args = parser.parse_args()

    with open(args.testcases_file, "r", encoding="utf-8") as f:
        text = f.read()

    parts = split_test_cases(text)
    tests = []
    for p in parts:
        title, steps = extract_title_and_steps(p)
        tests.append((title, steps))

    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    class_name = f"GeneratedTests_{slugify(args.issue_key)[:30]}_{ts}"

    java_code = generate_java(class_name, tests)

    # target path for java test file
    dest_dir = os.path.join(args.target, "src", "test", "java", "ai", "generated")
    ensure_dir(dest_dir)

    file_path = os.path.join(dest_dir, f"{class_name}.java")
    with open(file_path, "w", encoding="utf-8") as out:
        out.write(java_code)

    print(f"Wrote {file_path} with {len(tests)} tests")


if __name__ == "__main__":
    main()
