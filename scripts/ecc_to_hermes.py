#!/usr/bin/env python3
"""ECC-to-Hermes skill converter.

Converts ECC skills (markdown + YAML frontmatter) into Hermes Agent SKILL.md format.
ECC and Hermes use nearly identical formats — the converter handles:
- Stripping ECC-specific frontmatter fields (origin, version)
- Normalizing category assignment
- Copying reference files, scripts, and templates

Usage:
  python ecc_to_hermes.py <ecc_skill_dir> <hermes_skill_name> [--category <cat>]
"""

from __future__ import annotations
import sys
import shutil
import re
from pathlib import Path


def convert_skill(
    ecc_skill_dir: str | Path,
    hermes_name: str,
    category: str = "software-development",
    dry_run: bool = False,
) -> dict:
    """Convert an ECC skill directory to Hermes format.

    Args:
        ecc_skill_dir: Path to the ECC skill directory (contains SKILL.md)
        hermes_name: Target Hermes skill name
        category: Hermes skill category
        dry_run: If True, print what would be done without writing

    Returns:
        Dict with conversion stats
    """
    ecc_path = Path(ecc_skill_dir)
    if not ecc_path.is_dir():
        raise NotADirectoryError(f"ECC skill directory not found: {ecc_path}")

    skill_md = ecc_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"No SKILL.md found in {ecc_path}")

    # Read original content
    content = skill_md.read_text(encoding="utf-8")

    # Parse frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError(f"No YAML frontmatter found in {skill_md}")

    frontmatter_text = frontmatter_match.group(1)
    body = content[frontmatter_match.end() :]

    # Strip ECC-specific fields from frontmatter
    ecc_fields = ["origin:", "version:"]
    cleaned_lines: list[str] = []
    for line in frontmatter_text.split("\n"):
        if any(line.strip().startswith(f) for f in ecc_fields):
            continue
        cleaned_lines.append(line)

    cleaned_fm = "\n".join(cleaned_lines)

    # Build Hermes SKILL.md
    hermes_content = f"---\n{cleaned_fm}\n---\n{body}"

    # Find reference files, templates, scripts
    linked_files = {"references": [], "templates": [], "scripts": [], "assets": []}
    for subdir_name, hermes_key in [
        ("references", "references"),
        ("templates", "templates"),
        ("scripts", "scripts"),
        ("assets", "assets"),
    ]:
        subdir = ecc_path / subdir_name
        if subdir.is_dir():
            for f in subdir.rglob("*"):
                if f.is_file() and f.name != ".gitkeep":
                    linked_files[hermes_key].append(str(f.relative_to(ecc_path)))

    # Determine Hermes skills directory
    hermes_skills = Path.home() / "AppData/Local/hermes/skills" / category
    target_dir = hermes_skills / hermes_name
    target_skill_md = target_dir / "SKILL.md"

    if dry_run:
        print(f"[DRY RUN] Would create: {target_skill_md}")
        print(f"[DRY RUN] ECC src: {ecc_path}")
        print("[DRY RUN] Frontmatter fields stripped: origin, version")
        print(f"[DRY RUN] Linked files: {sum(len(v) for v in linked_files.values())}")
        return {"status": "dry_run", "target": str(target_skill_md)}

    # Write SKILL.md
    target_dir.mkdir(parents=True, exist_ok=True)
    target_skill_md.write_text(hermes_content, encoding="utf-8")

    # Copy linked files
    copied = {"references": 0, "templates": 0, "scripts": 0, "assets": 0}
    for hermes_key, rel_paths in linked_files.items():
        for rel_path in rel_paths:
            src = ecc_path / rel_path
            dst = target_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dst)
                copied[hermes_key] += 1

    total = sum(copied.values())

    return {
        "status": "created",
        "target": str(target_skill_md),
        "frontmatter_lines": len(cleaned_lines),
        "body_lines": len(body.strip().split("\n")),
        "linked_files_copied": total,
        "copied": copied,
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ecc_dir = sys.argv[1]
    hermes_name = sys.argv[2]
    category = "software-development"
    dry_run = False

    for arg in sys.argv[3:]:
        if arg.startswith("--category="):
            category = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry_run = True

    result = convert_skill(ecc_dir, hermes_name, category, dry_run)
    print(f"[{'DRY-RUN' if dry_run else 'OK'}] {result['target']}")
    if not dry_run:
        print(f"  Frontmatter: {result['frontmatter_lines']} lines")
        print(f"  Body: {result['body_lines']} lines")
        print(f"  Linked files copied: {result['linked_files_copied']}")
        for k, v in result["copied"].items():
            if v > 0:
                print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
