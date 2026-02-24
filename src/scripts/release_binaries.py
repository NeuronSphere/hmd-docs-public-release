#!/usr/bin/env python3
"""Release NeuronSphere binaries based on open_binaries.csv."""

import argparse
import csv
import io
import os
import subprocess
import sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "open_binaries.csv")

TECH_TO_COMMANDS = {
    "Python": ["python"],
    "Docker": ["docker"],
    "Python, Typescript": ["python"],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Release NeuronSphere binaries.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Release only this specific repo.",
    )
    parser.add_argument(
        "--tech",
        type=str,
        choices=["python", "docker"],
        default=None,
        help="Filter by technology type.",
    )
    return parser.parse_args()


def build_commands(repo, version, tech):
    """Return list of release command lists for a given repo/tech combo."""
    tools = TECH_TO_COMMANDS.get(tech)
    if not tools:
        return []
    cmds = []
    for tool in tools:
        cmds.append([
            "hmd",
            "--repo-name", repo,
            "--repo-version", version,
            tool, "release",
        ])
    return cmds


def main():
    args = parse_args()
    csv_path = os.path.normpath(CSV_PATH)

    with open(csv_path, newline="") as f:
        content = f.read()

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    succeeded = 0
    failed = 0
    skipped = 0
    failures = []

    for row in rows:
        repo = row["Repository"]
        version = row["Version"].strip()
        tech = row["Tech"].strip()

        if args.repo and repo != args.repo:
            continue

        if not version:
            print(f"  SKIP {repo}: no version")
            skipped += 1
            continue

        if not tech:
            print(f"  SKIP {repo}: no tech")
            skipped += 1
            continue

        cmds = build_commands(repo, version, tech)
        if not cmds:
            print(f"  SKIP {repo}: unsupported tech '{tech}'")
            skipped += 1
            continue

        if args.tech:
            cmds = [c for c in cmds if c[4] == args.tech]
            if not cmds:
                skipped += 1
                continue

        for cmd in cmds:
            cmd_str = " ".join(cmd)
            if args.dry_run:
                print(f"  DRY-RUN: {cmd_str}")
                succeeded += 1
            else:
                print(f"  RUN: {cmd_str}")
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    failed += 1
                    failures.append(f"  FAILED: {cmd_str} (exit {result.returncode})")
                else:
                    succeeded += 1

    print(f"\nSummary: {succeeded} succeeded, {failed} failed, {skipped} skipped")
    if failures:
        print("\nFailures:")
        for f_msg in failures:
            print(f_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
