#!/usr/bin/env python3
"""Release NeuronSphere binaries based on open_binaries.csv."""

import argparse
import csv
import io
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "open_binaries.csv")
DEFAULT_SBOM_DIR = os.path.join(PROJECT_ROOT, "sboms")

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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force release even if already released at current version.",
    )
    parser.add_argument(
        "--sbom-dir",
        type=str,
        default=DEFAULT_SBOM_DIR,
        help=f"Directory for generated SBOMs (default: {DEFAULT_SBOM_DIR}).",
    )
    parser.add_argument(
        "--skip-sbom",
        action="store_true",
        help="Skip SBOM generation after releasing.",
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


def find_whl(repo, version):
    """Find the .whl file for a Python repo in the project root."""
    pkg_name = repo.replace("-", "_")
    whl_name = f"{pkg_name}-{version}-py3-none-any.whl"
    whl_path = os.path.join(PROJECT_ROOT, whl_name)
    if os.path.isfile(whl_path):
        return whl_path
    return None


def build_sbom_command(repo, version, tech, sbom_dir):
    """Return the SBOM generation command for a repo, or None if not applicable."""
    output = os.path.join(sbom_dir, f"{repo}-{version}.sbom.json")
    if tech in ("Python", "Python, Typescript"):
        whl = find_whl(repo, version)
        if not whl:
            return None
        return ["hmd", "release", "sbom", "--package", whl, "-o", output]
    elif tech == "Docker":
        return ["hmd", "release", "sbom", "--image", f"{repo}:{version}", "-o", output]
    return None


def main():
    args = parse_args()
    csv_path = os.path.normpath(CSV_PATH)

    with open(csv_path, newline="") as f:
        content = f.read()

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames
    rows = list(reader)

    if not args.skip_sbom:
        os.makedirs(args.sbom_dir, exist_ok=True)

    succeeded = 0
    failed = 0
    skipped = 0
    failures = []
    sbom_succeeded = 0
    sbom_failed = 0
    sbom_failures = []

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

        released_version = row.get("Released Version", "").strip()
        if not args.force and released_version == version:
            print(f"  SKIP {repo}: v{version} already released")
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

        repo_success = True
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
                    repo_success = False
                    failures.append(f"  FAILED: {cmd_str} (exit {result.returncode})")
                else:
                    succeeded += 1

        if repo_success and not args.dry_run:
            row["Released Version"] = version

        # Generate SBOM after successful release (or dry-run)
        if not args.skip_sbom and repo_success:
            sbom_cmd = build_sbom_command(repo, version, tech, args.sbom_dir)
            if sbom_cmd:
                sbom_cmd_str = " ".join(sbom_cmd)
                if args.dry_run:
                    print(f"  DRY-RUN SBOM: {sbom_cmd_str}")
                    sbom_succeeded += 1
                else:
                    print(f"  SBOM: {sbom_cmd_str}")
                    result = subprocess.run(sbom_cmd)
                    if result.returncode != 0:
                        sbom_failed += 1
                        sbom_failures.append(
                            f"  FAILED SBOM: {sbom_cmd_str} (exit {result.returncode})"
                        )
                    else:
                        sbom_succeeded += 1

    # Write updated CSV back with Released Version tracking
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nRelease summary: {succeeded} succeeded, {failed} failed, {skipped} skipped")
    if not args.skip_sbom:
        print(f"SBOM summary: {sbom_succeeded} succeeded, {sbom_failed} failed")
    if failures:
        print("\nRelease failures:")
        for f_msg in failures:
            print(f_msg)
    if sbom_failures:
        print("\nSBOM failures:")
        for f_msg in sbom_failures:
            print(f_msg)
    if failures or sbom_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
