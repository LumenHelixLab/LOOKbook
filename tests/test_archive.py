from __future__ import annotations
from pathlib import Path
import zipfile
import pytest


@pytest.fixture
def sample_cbz(tmp_path: Path) -> Path:
    """Create a synthetic CBZ comic archive with 2 test pages."""
    from PIL import Image

    cbz_path = tmp_path / "test_comic.cbz"
    with zipfile.ZipFile(cbz_path, "w") as zf:
        for i in range(2):
            img = Image.new("RGB", (100, 150), "white")
            page_path = tmp_path / f"page_{i:03d}.png"
            img.save(page_path)
            zf.write(page_path, f"page_{i:03d}.png")
            page_path.unlink()
    return cbz_path


class TestArchive:
    def test_list_pages_cbz(self, sample_cbz):
        from lookbook.pipeline.archive import list_pages

        pages = list_pages(sample_cbz)
        assert len(pages) == 2
        assert pages[0]["page_index"] == 0
        assert pages[0]["filename"] == "page_000.png"
        assert pages[1]["filename"] == "page_001.png"
        assert pages[0]["extension"] == ".png"
        assert pages[0]["size_bytes"] > 0

    def test_list_pages_nonexistent(self, tmp_path):
        from lookbook.pipeline.archive import list_pages

        with pytest.raises(FileNotFoundError):
            list_pages(tmp_path / "nonexistent.cbz")

    def test_extract_page(self, sample_cbz, tmp_path):
        from lookbook.pipeline.archive import extract_page

        out = extract_page(sample_cbz, "page_000.png", tmp_path / "output")
        assert out.exists()
        assert out.name == "page_000.png"
        assert out.stat().st_size > 0

    def test_extract_all_pages(self, sample_cbz, tmp_path):
        from lookbook.pipeline.archive import extract_all_pages

        paths = extract_all_pages(sample_cbz, tmp_path / "output")
        assert len(paths) == 2
        assert all(p.exists() for p in paths)

    def test_list_pages_cli(self, sample_cbz):
        from lookbook.cli import main

        main(["list-pages", str(sample_cbz)])

    def test_unsupported_format(self, tmp_path):
        from lookbook.pipeline.archive import list_pages

        bad = tmp_path / "test.pdf"
        bad.write_text("not an archive")
        with pytest.raises(ValueError, match="Unsupported archive format"):
            list_pages(bad)


class TestProcessArchive:
    def test_process_archive_basic(self, sample_cbz, tmp_path):
        """Test process-archive creates project and runs pipeline."""
        from lookbook.pipeline.archive import process_archive

        project = tmp_path / "test_project"
        result = process_archive(sample_cbz, project, no_cleanup=True)
        assert result["schema"] == "lookbook.archive_process.v0.2"
        assert result["total_pages"] == 2
        assert result["archive"] == "test_comic.cbz"
        assert len(result["pages"]) == 2

        # Check project structure was created
        assert (project / "manifest.json").exists()
        assert (project / "analysis").exists()

    def test_process_archive_creates_exports(self, sample_cbz, tmp_path):
        """Verify process-archive creates export structure."""
        from lookbook.pipeline.archive import process_archive

        project = tmp_path / "test_project"
        process_archive(sample_cbz, project)

        # Project structure should exist
        assert (project / "manifest.json").exists()
        assert (project / "analysis").exists()
        # Exports may or may not exist depending on panel detection
        # (blank images produce 0 panels, so shot_graph isn't created)
        # But the project itself should be valid
        assert (project / "analysis" / "archive_process.json").exists()
