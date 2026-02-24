#!/usr/bin/env python3
"""Update open_binaries.csv with latest git tag versions from local repos."""

import csv
import io
import os
import re
import subprocess
import sys
from datetime import datetime

PROJECTS_DIR = "/Users/aburg/hmdtr1/projects"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "open_binaries.csv")
TODAY = datetime.now().strftime("%Y-%b-%d")


def get_latest_tag(repo_name):
    """Get the latest semver tag from a local git repo."""
    repo_path = os.path.join(PROJECTS_DIR, repo_name)
    if not os.path.isdir(repo_path):
        return None, f"directory not found: {repo_path}"
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "tag", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None, f"git tag failed: {result.stderr.strip()}"
        tags = result.stdout.strip().splitlines()
        if not tags or not tags[0]:
            return None, "no tags found"
        return tags[0], None
    except subprocess.TimeoutExpired:
        return None, "git tag timed out"


def parse_version(version_str):
    """Parse a version string like '1.2.303' into a tuple of ints for comparison."""
    parts = re.findall(r"\d+", version_str)
    return tuple(int(p) for p in parts)


def is_newer(tag, current):
    """Return True if tag is a newer version than current."""
    try:
        return parse_version(tag) > parse_version(current)
    except (ValueError, IndexError):
        return False


def main():
    csv_path = os.path.normpath(CSV_PATH)

    with open(csv_path, newline="") as f:
        content = f.read()

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames
    rows = list(reader)

    updated = 0
    skipped = 0
    errors = []

    for row in rows:
        repo = row["Repository"]
        tag, err = get_latest_tag(repo)
        if err:
            errors.append(f"  SKIP {repo}: {err}")
            skipped += 1
            continue
        old_version = row["Version"]
        if not old_version:
            row["Version"] = tag
            row["Date"] = TODAY
            updated += 1
            print(f"  UPDATE {repo}: (empty) -> {tag}")
        elif is_newer(tag, old_version):
            row["Version"] = tag
            row["Date"] = TODAY
            updated += 1
            print(f"  UPDATE {repo}: {old_version} -> {tag}")
        elif tag != old_version:
            print(f"  KEEP   {repo}: {old_version} (tag {tag} is not newer)")
        else:
            print(f"  OK     {repo}: {old_version} (unchanged)")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSummary: {updated} updated, {skipped} skipped, {len(rows) - updated - skipped} unchanged")
    if errors:
        print("\nSkipped repos:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
