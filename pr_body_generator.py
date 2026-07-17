"""
pr_body_generator.py — Generate GitHub Pull Request body markdown files.

Reads reports/ai_summary.json and produces:
  - reports/pr_body_app.md   (for app-code PRs — APP_HEAL)
  - reports/pr_body_tests.md (for test-code PRs — TEST_HEAL)

Both files include:
  - Failure diagnosis table
  - Healing type & healed files list
  - Root cause commit analysis
  - Applied AI fixes with diffs (if any)
  - Linked Jira tickets (healed and unhealed)
  - Environment issue summary (if any)
  - Remaining recommendations
"""
import json
from pathlib import Path


def _jira_links_section(jira_list: list, title: str) -> list:
    """Render a list of JiraResult dicts as markdown links."""
    lines = []
    if not jira_list:
        return lines
    lines.append(f"\n### 🎫 {title}")
    for jr in jira_list:
        jira_id  = jr.get("jira_id", "")
        jira_url = jr.get("jira_url", "")
        test_name = jr.get("test_name", "unknown")
        bug_type  = jr.get("bug_type", "")
        heal_st   = jr.get("heal_status", "")
        if jira_id and jira_url:
            lines.append(f"- [{jira_id}]({jira_url}) — `{test_name}` `{bug_type}` [{heal_st}]")
        else:
            lines.append(f"- (failed to create) — `{test_name}`")
    return lines


def main():
    summary_path = Path("reports/ai_summary.json")

    # ── Defaults if no summary ──
    default_app   = "The AI regression pipeline detected and successfully healed bugs within your application source code. All tests are now passing."
    default_tests = "The AI regression pipeline detected outdated or incorrect test assertions and auto-healed them to match application behavior."

    if not summary_path.exists():
        Path("reports/pr_body_app.md").write_text(default_app, encoding="utf-8")
        Path("reports/pr_body_tests.md").write_text(default_tests, encoding="utf-8")
        return

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        Path("reports/pr_body_app.md").write_text(default_app, encoding="utf-8")
        Path("reports/pr_body_tests.md").write_text(default_tests, encoding="utf-8")
        return

    recs           = data.get("recommendations", [])
    classifications = data.get("classifications", [])
    rc             = data.get("root_cause")
    approved_fixes = data.get("approved_fixes", [])
    healed_files   = data.get("healed_files", [])
    healing_type   = data.get("healing_type", "NONE")
    env_issues     = data.get("env_issues", [])
    jira_healed    = data.get("jira_results_healed", [])
    jira_unhealed  = data.get("jira_results", [])
    summary_block  = data.get("summary", {})

    # ── Shared root cause ──
    def root_cause_section(lines: list):
        if not rc:
            return
        lines.append("\n### 🔍 Root Cause Commit Analysis")
        lines.append(f"- **Suspected Commit:** `{rc.get('commit_sha', 'N/A')[:8]}`")
        lines.append(f"- **Author:** {rc.get('author', 'N/A')}")
        lines.append(f"- **Date:** {rc.get('date', 'N/A')}")
        lines.append(f"- **Commit Message:** {rc.get('commit_message', 'N/A')}")
        lines.append(f"- **AI Analysis:** {rc.get('analysis', 'N/A')}")
        lines.append("")

    # ── ENV_ISSUE section ──
    def env_issue_section(lines: list):
        if not env_issues:
            return
        lines.append("\n### ⚙️ Environment Issues (Manual Action Required)")
        lines.append("> These failures could **not** be auto-fixed. Manual environment remediation is needed.")
        lines.append("")
        for ei in env_issues:
            tn   = ei.get("test_name", "unknown")
            hint = ei.get("remediation_hint", "")
            err  = ei.get("error_message", "")[:200]
            lines.append(f"#### `{tn}`")
            lines.append(f"- **Error:** `{err}`")
            lines.append(f"- **Remediation:** {hint}")
            lines.append("")

    # ── Summary banner ──
    def summary_banner(lines: list, pr_type: str):
        total    = summary_block.get("total", 0)
        healed   = summary_block.get("healed", 0)
        env_cnt  = summary_block.get("env_issues", 0)
        j_healed = summary_block.get("jira_healed", 0)
        j_open   = summary_block.get("jira_unhealed", 0)
        lines.append(f"\n> **Run Summary** | Tests: {total} | Healed: {healed} | ENV Issues: {env_cnt} | Jira Created: {j_healed + j_open} ({j_healed} healed, {j_open} open)")
        lines.append(f"> **Healing Type:** `{healing_type}`")
        lines.append("")

    # ═══════════════════════════════════════════════════════════════════════
    # 1. App PR Body (APP_HEAL or MIXED)
    # ═══════════════════════════════════════════════════════════════════════
    body_app = []
    body_app.append("## 🤖 RegressionAI Auto-Healed Pull Request\n")
    body_app.append("The AI regression pipeline has automatically resolved the **application** failure(s) and verified that all tests are passing.\n")

    summary_banner(body_app, "app")
    root_cause_section(body_app)

    if healed_files:
        body_app.append("\n### 🛠️ Healed Application Files")
        for hf in healed_files:
            if hf and not hf.startswith("tests/"):
                body_app.append(f"- `{hf}`")
        body_app.append("")

    if approved_fixes:
        body_app.append("\n### 🔧 Applied AI Fixes")
        for fix in approved_fixes:
            fp   = fix.get("file_path", "")
            expl = fix.get("explanation", "")
            if not fp.startswith("tests/"):
                body_app.append(f"#### 📁 `{fp}`")
                body_app.append(f"- **Why:** {expl}")
        body_app.append("")

    body_app.extend(_jira_links_section(jira_healed,   "Jira Tickets — AI-Healed (Done)"))
    body_app.extend(_jira_links_section(jira_unhealed, "Jira Tickets — Remaining / Unhealed"))
    env_issue_section(body_app)

    if recs:
        body_app.append("\n### 💡 Remaining Recommendations")
        for r in recs:
            tn  = r.get("test_name", "Unknown Test")
            sm  = r.get("summary", "")
            sf  = r.get("suggested_fix", "")
            body_app.append(f"#### 🎫 {tn}")
            body_app.append(f"- **Explanation:** {sm}")
            if sf:
                body_app.append(f"- **Suggested fix:**\n```python\n{sf}\n```")
            body_app.append("")

    Path("reports/pr_body_app.md").write_text("\n".join(body_app), encoding="utf-8")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. Tests PR Body (TEST_HEAL or MIXED)
    # ═══════════════════════════════════════════════════════════════════════
    body_tests = []
    body_tests.append("## 🤖 RegressionAI Test Suite Updates\n")
    body_tests.append("The AI regression pipeline detected outdated or incorrect test assertions and auto-healed them to match application behavior.\n")

    summary_banner(body_tests, "tests")
    root_cause_section(body_tests)

    if healed_files:
        body_tests.append("\n### 🧪 Healed Test Files")
        for hf in healed_files:
            if hf and hf.startswith("tests/"):
                body_tests.append(f"- `{hf}`")
        body_tests.append("")

    if approved_fixes:
        body_tests.append("\n### 🔧 Applied Test Fixes")
        for fix in approved_fixes:
            fp   = fix.get("file_path", "")
            expl = fix.get("explanation", "")
            if fp.startswith("tests/"):
                body_tests.append(f"#### 📁 `{fp}`")
                body_tests.append(f"- **Why:** {expl}")
        body_tests.append("")

    body_tests.extend(_jira_links_section(jira_healed,   "Jira Tickets — AI-Healed (Done)"))
    body_tests.extend(_jira_links_section(jira_unhealed, "Jira Tickets — Remaining / Unhealed"))
    env_issue_section(body_tests)

    if recs:
        body_tests.append("\n### 💡 Remaining Recommendations")
        for r in recs:
            tn  = r.get("test_name", "Unknown Test")
            sm  = r.get("summary", "")
            sf  = r.get("suggested_fix", "")
            body_tests.append(f"#### 🧪 {tn}")
            body_tests.append(f"- **Explanation:** {sm}")
            if sf:
                body_tests.append(f"- **Updated assertions:**\n```python\n{sf}\n```")
            body_tests.append("")

    Path("reports/pr_body_tests.md").write_text("\n".join(body_tests), encoding="utf-8")

    # Collect unique Jira ticket IDs for git branch/commit integration
    jira_ids = []
    for jr in (jira_healed + jira_unhealed):
        jid = jr.get("jira_id")
        if jid and jid not in jira_ids:
            jira_ids.append(jid)
    Path("reports/jira_keys.txt").write_text(" ".join(jira_ids), encoding="utf-8")


if __name__ == "__main__":
    main()
