"""lookBOOK — News & Docs Page Exporter

Generates a standalone HTML news/docs page from markdown trackers
in the docs/ directory. Lightweight: no external markdown parser
required; uses basic regex substitution for common markdown syntax.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..models import write_json


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_to_html(md: str) -> str:
    """Naive but sufficient markdown → HTML for lookBOOK docs."""
    html = md
    placeholders: dict[str, str] = {}
    counter = 0

    def _ph(content: str) -> str:
        nonlocal counter
        key = f"__PH_{counter}__"
        counter += 1
        placeholders[key] = content
        return key

    # Protect code blocks first
    def _code_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = _escape_html(m.group(2))
        return _ph(f'<pre class="code-block" data-lang="{lang}"><code>{code}</code></pre>')

    html = re.sub(r"```(\w*)\n(.*?)```", _code_block, html, flags=re.S)

    # Protect inline code
    def _inline_code(m: re.Match) -> str:
        return _ph(f"<code>{_escape_html(m.group(1))}</code>")

    html = re.sub(r"`([^`]+)`", _inline_code, html)

    # Headers
    html = re.sub(r"^###### (.+)$", r"<h6>\1</h6>", html, flags=re.M)
    html = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", html, flags=re.M)
    html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.M)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.M)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.M)

    # Bold / italic
    html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Links [text](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', html)

    # Horizontal rules
    html = re.sub(r"^---+$", r"<hr>", html, flags=re.M)

    # Blockquotes
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.M)

    # Unordered lists
    def _ul(m: re.Match) -> str:
        items = m.group(1)
        lis = re.sub(r"^\s*[-*] (.+)$", r"<li>\1</li>", items, flags=re.M)
        return f"<ul>{lis}</ul>"

    html = re.sub(r"((?:^\s*[-*] .+\n?)+)", _ul, html, flags=re.M)

    # Ordered lists
    def _ol(m: re.Match) -> str:
        items = m.group(1)
        lis = re.sub(r"^\s*\d+\. (.+)$", r"<li>\1</li>", items, flags=re.M)
        return f"<ol>{lis}</ol>"

    html = re.sub(r"((?:^\s*\d+\. .+\n?)+)", _ol, html, flags=re.M)

    # Tables (simple pipe tables)
    def _table(m: re.Match) -> str:
        lines = m.group(0).strip().split("\n")
        rows = [line for line in lines if not re.match(r"^\|?\s*:?-+", line)]
        thead = ""
        tbody = ""
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.split("|")]
            # Remove empty leading/trailing from pipe table syntax
            cells = [c for c in cells if c or c == ""]
            while cells and cells[0] == "":
                cells = cells[1:]
            while cells and cells[-1] == "":
                cells = cells[:-1]
            tds = "".join(f"<td>{_escape_html(c)}</td>" for c in cells)
            if i == 0:
                thead = f"<tr>{tds}</tr>"
            else:
                tbody += f"<tr>{tds}</tr>"
        return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"

    html = re.sub(r"(^\|? .+ \|\n\|?[-:| ]+\|\n(?:\|? .+ \|\n?)+)", _table, html, flags=re.M)

    # Paragraphs (wrap remaining text blocks)
    paragraphs = []
    for block in html.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("<"):
            paragraphs.append(block)
        else:
            inner = "<br>\n".join(block.split("\n"))
            paragraphs.append(f"<p>{inner}</p>")
    html = "\n\n".join(paragraphs)

    # Restore placeholders
    for key, val in placeholders.items():
        html = html.replace(key, val)

    return html


def export_docs(
    project: str | Path,
    output_name: str = "news_and_docs.html",
    docs_dir: str | Path | None = None,
) -> Path:
    """Generate a unified HTML news & docs page from markdown trackers.

    Args:
        project: lookBOOK project path
        output_name: filename for the generated HTML
        docs_dir: directory containing .md tracker files (defaults to repo docs/)

    Returns:
        Path to the generated HTML file.
    """
    project = Path(project)
    out_dir = project / "exports" / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    if docs_dir is None:
        import lookbook

        docs_dir = Path(lookbook.__file__).parent.parent / "docs"
    else:
        docs_dir = Path(docs_dir)

    sections: list[dict[str, Any]] = []
    if docs_dir.exists():
        for md_file in sorted(docs_dir.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            sections.append({
                "title": md_file.stem.replace("_", " ").title(),
                "source": str(md_file),
                "html": _md_to_html(raw),
            })

    style = """
    :root{--bg:#070a10;--fg:#fdf6d8;--accent:#1ae0cf;--muted:#8a9ab0;--surface:#121824;--border:#1e2a3a}
    *{box-sizing:border-box}
    body{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,sans-serif;margin:0;line-height:1.6}
    header{max-width:1100px;margin:auto;padding:40px 20px 0}
    .badge{color:var(--accent);text-transform:uppercase;letter-spacing:.18em;font-weight:800;font-size:.75rem}
    h1{font-size:2.2rem;margin:.2em 0 .6em}
    .sub{color:var(--muted);font-size:.95rem}
    main{max-width:1100px;margin:auto;padding:20px}
    article{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px 32px;margin-bottom:24px}
    article h2{margin-top:0;color:var(--accent);font-size:1.4rem}
    h3{color:var(--fg);font-size:1.15rem;margin-top:1.4em}
    h4{font-size:1rem;color:var(--muted);margin-top:1.2em}
    p{margin:.6em 0}
    a{color:var(--accent);text-decoration:none}
    a:hover{text-decoration:underline}
    code{background:rgba(26,224,207,.12);padding:.15em .4em;border-radius:4px;font-size:.9em}
    pre.code-block{background:#0b101a;border:1px solid var(--border);border-radius:12px;padding:16px;overflow:auto}
    pre.code-block code{background:transparent;padding:0}
    table{width:100%;border-collapse:collapse;margin:1em 0;font-size:.92rem}
    th,td{border:1px solid var(--border);padding:10px 12px;text-align:left}
    thead{background:var(--bg)}
    th{color:var(--accent);font-weight:600}
    tr:nth-child(even){background:rgba(255,255,255,.02)}
    ul,ol{margin:.6em 0;padding-left:1.4em}
    li{margin:.25em 0}
    blockquote{border-left:3px solid var(--accent);margin:.8em 0;padding-left:14px;color:var(--muted)}
    hr{border:0;border-top:1px solid var(--border);margin:1.4em 0}
    .timestamp{font-size:.8rem;color:var(--muted);margin-top:4px}
    footer{text-align:center;color:var(--muted);font-size:.8rem;padding:30px 20px}
    """

    nav_links = ""
    for s in sections:
        anchor = s["title"].lower().replace(" ", "-")
        nav_links += f'<a href="#{anchor}">{s["title"]}</a> · '
    nav_links = nav_links.rstrip(" · ")

    body_parts = []
    for s in sections:
        anchor = s["title"].lower().replace(" ", "-")
        body_parts.append(f'<article id="{anchor}">\n<h2>{s["title"]}</h2>\n{s["html"]}\n</article>')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lookBOOK News & Docs</title>
<style>{style}</style>
</head>
<body>
<header>
<p class="badge">lookBOOK News & Docs</p>
<h1>Project News & External Tool Tracker</h1>
<p class="sub">Curated intelligence on NotebookLM, AI APIs, and pipeline-relevant tooling.</p>
<p class="sub">{nav_links}</p>
</header>
<main>
{chr(10).join(body_parts)}
</main>
<footer>Generated by lookBOOK · {__import__('datetime').datetime.now().isoformat()[:10]}</footer>
</body>
</html>"""

    out_path = out_dir / output_name
    out_path.write_text(html, encoding="utf-8")

    write_json(
        out_dir / "docs_index.json",
        {
            "schema": "lookbook.docs_export.v0.1",
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "html_path": str(out_path.relative_to(project)),
            "sections": [{"title": s["title"], "source": s["source"]} for s in sections],
        },
    )

    return out_path
