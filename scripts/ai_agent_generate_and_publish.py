#!/usr/bin/env python3
"""
Run the test-case notebook, extract generated test cases, and invoke the Java test generator.

Usage:
  python scripts/ai_agent_generate_and_publish.py --notebook ../testCaseGeneratorAgent.ipynb \
      --out ./generated_testcases.txt --target /absolute/path/to/playwright-project
"""
import argparse
import sys
import subprocess
from pathlib import Path


def ensure_deps():
    try:
        import nbformat  # noqa: F401
        from nbclient import NotebookClient  # noqa: F401
    except Exception:
        print('Installing nbformat and nbclient...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'nbformat', 'nbclient'])


def run_notebook(nb_path: Path, timeout: int = 600) -> str:
    import nbformat
    from nbclient import NotebookClient
    import re

    nb = nbformat.read(str(nb_path), as_version=4)

    # Fast path: some notebooks include a demo `test_cases = """..."""` fallback
    for cell in nb.cells:
        src = "\n".join(cell.get('source', [])) if isinstance(cell.get('source', []), list) else str(cell.get('source'))
        m = re.search(r'test_cases\s*=\s*"""(.*?)"""', src, flags=re.DOTALL)
        if m:
            print('Found embedded demo test_cases in notebook; using fallback content')
            return m.group(1).strip()

    # Modify the ISSUE cell to avoid NameError if helper is missing
    for cell in nb.cells:
        src_list = cell.get('source', [])
        if isinstance(src_list, list):
            for i, line in enumerate(src_list):
                if 'get_issue_summary_and_description' in line:
                    # replace the single line with a safe try/except block
                    try_block = [
                        'try:',
                        '    info = get_issue_summary_and_description(ISSUE_KEY)',
                        'except Exception:',
                        '    info = {"summary": ISSUE_KEY, "description": ""}',
                    ]
                    # replace that line in the source
                    new_src = src_list[:i] + try_block + src_list[i+1:]
                    cell['source'] = new_src
                    break

    # Inject fallback helper if notebook doesn't define it
    has_helper = any('get_issue_summary_and_description' in ("\n".join(cell.get('source', [])) if isinstance(cell.get('source', []), list) else str(cell.get('source')) ) for cell in nb.cells)
    if not has_helper:
        helper_src = [
            "def get_issue_summary_and_description(issue_key):",
            "    try:",
            "        # Try to use JiraAPIWrapper if available",
            "        from langchain_community.utilities import JiraAPIWrapper",
            "        jira = JiraAPIWrapper()",
            "        issue = jira.get_issue(issue_key)",
            "        fields = issue.get('fields', {})",
            "        summary = fields.get('summary', '')",
            "        description = fields.get('description', '') or ''",
            "        return {'summary': summary, 'description': description}",
            "    except Exception:",
            "        # Fallback: minimal info so notebook can continue",
            "        return {'summary': issue_key, 'description': 'No description available (fallback)'}",
        ]
        # Insert helper right before the cell that sets ISSUE_KEY so it's defined after any environment/setup cells
        insert_idx = 0
        for i, cell in enumerate(nb.cells):
            src = "\n".join(cell.get('source', [])) if isinstance(cell.get('source', []), list) else str(cell.get('source'))
            if 'ISSUE_KEY' in src and 'MBA-8' in src:
                insert_idx = i
                break
        nb.cells.insert(insert_idx, {'cell_type': 'code', 'metadata': {'language': 'python'}, 'source': helper_src})

    client = NotebookClient(nb, timeout=timeout, kernel_name='python3')
    print(f'Executing notebook: {nb_path}')
    client.execute()

    all_stream = ''
    for c in nb.cells:
        for o in c.get('outputs', []):
            if o.get('output_type') == 'stream':
                all_stream += o.get('text', '')

    m = re.search(r'Generated Test Cases:\n(.*?)(?:\n={10,}|$)', all_stream, flags=re.DOTALL)
    if not m:
        print('Could not find "Generated Test Cases:" in notebook output. Dumping stream (first 4000 chars):')
        print(all_stream[:4000])
        raise RuntimeError('Test cases not found in executed notebook output')

    return m.group(1).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--notebook', required=False, default='testCaseGeneratorAgent.ipynb')
    parser.add_argument('--out', required=False, default='generated_testcases.txt')
    parser.add_argument('--target', required=False, default='/Users/hari.durai/automationProject/agentic-ai-automation-test')
    args = parser.parse_args()

    nb_path = Path(args.notebook)
    if not nb_path.exists():
        raise FileNotFoundError(f'Notebook not found: {nb_path}')

    ensure_deps()

    testcases = run_notebook(nb_path)
    out_file = Path(args.out)
    out_file.write_text(testcases, encoding='utf-8')
    print(f'Wrote extracted test cases to: {out_file.resolve()}')

    # Invoke generator script
    gen_script = Path(__file__).parent / 'generate_playwright_java_tests.py'
    if not gen_script.exists():
        raise FileNotFoundError(f'Generator script not found: {gen_script}')

    cmd = [sys.executable, str(gen_script), '--testcases-file', str(out_file), '--issue-key', 'MBA-8', '--target', args.target]
    print('Running generator script:', ' '.join(cmd))
    subprocess.check_call(cmd)
    print('Generator script completed')


if __name__ == '__main__':
    main()
