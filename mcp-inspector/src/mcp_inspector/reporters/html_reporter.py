import html
import sys


_SEVERITY_ORDER = ("critical", "high", "medium", "low")


def generate_html(report: dict) -> str:
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    status = _status_text(summary)

    rows = "\n".join(_finding_card(finding) for finding in findings)
    if not rows:
        rows = """
        <section class="empty">
          <h2>No findings</h2>
          <p>This scan did not find high-risk MCP, app config, or repository secret issues.</p>
        </section>
        """.strip()

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>mcp-inspector report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #626b76;
      --line: #d7dce2;
      --critical: #b42318;
      --high: #b54708;
      --medium: #8a6a00;
      --low: #175cd3;
      --ok: #067647;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 20px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    p {{ margin: 0; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin: 20px 0;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric strong {{
      display: block;
      font-size: 26px;
      line-height: 1;
      margin-bottom: 6px;
    }}
    .metric span {{
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
    }}
    .finding, .empty {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-top: 12px;
      padding: 18px;
    }}
    .finding-header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}
    .finding-title {{
      min-width: 0;
    }}
    .rule {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      color: var(--muted);
      overflow-wrap: anywhere;
    }}
    .badge {{
      border-radius: 999px;
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      padding: 5px 9px;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .badge.critical {{ background: var(--critical); }}
    .badge.high {{ background: var(--high); }}
    .badge.medium {{ background: var(--medium); }}
    .badge.low {{ background: var(--low); }}
    .metric.critical {{ border-top: 4px solid var(--critical); }}
    .metric.high {{ border-top: 4px solid var(--high); }}
    .metric.medium {{ border-top: 4px solid var(--medium); }}
    .metric.low {{ border-top: 4px solid var(--low); }}
    .ok {{ color: var(--ok); }}
    dl {{
      display: grid;
      grid-template-columns: minmax(120px, 180px) 1fr;
      gap: 8px 14px;
      margin: 0;
    }}
    dt {{
      color: var(--muted);
      font-weight: 600;
    }}
    dd {{
      margin: 0;
      min-width: 0;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 640px) {{
      main {{ padding: 24px 14px 36px; }}
      h1 {{ font-size: 24px; }}
      .finding-header {{ display: block; }}
      .badge {{
        display: inline-block;
        margin-top: 10px;
      }}
      dl {{ grid-template-columns: 1fr; }}
      dt {{ margin-top: 8px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>mcp-inspector report</h1>
      <div class="meta">
        <p><strong>Target:</strong> {_e(report.get("scan_target", ""))}</p>
        <p><strong>Scan time:</strong> {_e(report.get("scan_time", ""))}</p>
        <p><strong>Status:</strong> {_e(status)}</p>
      </div>
    </header>
    <section class="summary" aria-label="Findings summary">
      {_metric("Total", summary.get("total", 0))}
      {_metric("Critical", summary.get("critical", 0), "critical")}
      {_metric("High", summary.get("high", 0), "high")}
      {_metric("Medium", summary.get("medium", 0), "medium")}
      {_metric("Low", summary.get("low", 0), "low")}
    </section>
    <section aria-label="Findings">
      {rows}
    </section>
  </main>
</body>
</html>
"""


def print_html(report: dict) -> None:
    print(generate_html(report))


def write_html(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(generate_html(report))
    print(f"HTML report written to: {path}", file=sys.stderr)


def _finding_card(finding: dict) -> str:
    severity = str(finding.get("severity", "low")).lower()
    if severity not in _SEVERITY_ORDER:
        severity = "low"
    return f"""
      <article class="finding">
        <div class="finding-header">
          <div class="finding-title">
            <h2>{_e(finding.get("title", ""))}</h2>
            <div class="rule">{_e(finding.get("id", ""))}</div>
          </div>
          <span class="badge {severity}">{_e(severity)}</span>
        </div>
        <dl>
          <dt>Category</dt>
          <dd>{_e(finding.get("category", ""))}</dd>
          <dt>Source</dt>
          <dd>{_e(finding.get("source", ""))}</dd>
          <dt>Evidence</dt>
          <dd>{_e(finding.get("evidence", ""))}</dd>
          <dt>Why it matters</dt>
          <dd>{_e(finding.get("why_it_matters", ""))}</dd>
          <dt>Recommended fix</dt>
          <dd>{_e(finding.get("recommended_fix", ""))}</dd>
          <dt>Confidence</dt>
          <dd>{_e(finding.get("confidence", ""))}</dd>
        </dl>
      </article>
    """.rstrip()


def _metric(label: str, value: object, severity: str = "") -> str:
    class_name = f"metric {severity}".strip()
    return f"""<div class="{class_name}"><strong>{_e(value)}</strong><span>{_e(label)}</span></div>"""


def _status_text(summary: dict) -> str:
    if summary.get("critical", 0):
        return "Unsafe - critical issues found"
    if summary.get("high", 0):
        return "Unsafe - action required"
    if summary.get("medium", 0) or summary.get("low", 0):
        return "Review recommended"
    return "No findings"


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
