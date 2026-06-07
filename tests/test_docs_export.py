"""Tests for docs/news page exporter."""

from pathlib import Path

from lookbook.pipeline.docs_export import _md_to_html, export_docs


class TestMdToHtml:
    def test_headers(self):
        md = "# H1\n## H2\n### H3"
        html = _md_to_html(md)
        assert "<h1>H1</h1>" in html
        assert "<h2>H2</h2>" in html
        assert "<h3>H3</h3>" in html

    def test_bold_and_italic(self):
        md = "**bold** and *italic*"
        html = _md_to_html(md)
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_link(self):
        md = "[text](https://example.com)"
        html = _md_to_html(md)
        assert '<a href="https://example.com" target="_blank">text</a>' in html

    def test_code_inline(self):
        md = "use `print()` here"
        html = _md_to_html(md)
        assert "<code>print()</code>" in html

    def test_code_block(self):
        md = "```python\nx = 1\n```"
        html = _md_to_html(md)
        assert '<pre class="code-block"' in html
        assert "x = 1" in html

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = _md_to_html(md)
        assert "<table>" in html
        assert "<td>1</td>" in html

    def test_blockquote(self):
        md = "> quote"
        html = _md_to_html(md)
        assert "<blockquote>quote</blockquote>" in html

    def test_hr(self):
        md = "---"
        html = _md_to_html(md)
        assert "<hr>" in html


class TestExportDocs:
    def test_generates_html(self, tmp_path: Path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "TEST_TRACKER.md").write_text("# Test\n\nHello world.", encoding="utf-8")

        project = tmp_path / "proj"
        project.mkdir()

        path = export_docs(project, docs_dir=docs_dir)
        assert path.exists()
        html = path.read_text(encoding="utf-8")
        assert "lookBOOK News & Docs" in html
        assert "Test Tracker" in html
        assert "Hello world." in html

    def test_generates_index_json(self, tmp_path: Path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "A.md").write_text("# A", encoding="utf-8")

        project = tmp_path / "proj"
        project.mkdir()

        export_docs(project, docs_dir=docs_dir)
        index = project / "exports" / "docs" / "docs_index.json"
        assert index.exists()
        data = __import__("json").loads(index.read_text(encoding="utf-8"))
        assert data["schema"].startswith("lookbook.docs")
        assert len(data["sections"]) == 1
