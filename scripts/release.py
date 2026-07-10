#!/usr/bin/env -S uv run python
"""
Cut a new shpyx release.

The published version is derived from the git tag (via hatch-vcs), so releasing
is simply a matter of pushing a `v*` tag to `main`. This script does that safely:

  1. Verify the working tree is clean and on `main`.
  2. Fetch and fast-forward to `origin/main`.
  3. Look up the latest version currently on PyPI.
  4. Let the user pick the next version (patch / minor / major).
  5. If the tag already exists (e.g. a previous release run failed), offer to
     delete it first.
  6. Create the tag and push it, which triggers the `Release` GitHub Action.

Run from the repository root with `./scripts/release.py` (the shebang uses `uv run`,
so shpyx and its environment are set up automatically).
"""

import json
import sys
import urllib.request

import shpyx

PYPI_URL = "https://pypi.org/pypi/shpyx/json"
MAIN_BRANCH = "main"


def abort(message: str) -> None:
    """Print an error and exit with a non-zero status."""
    print(f"\n❌ {message}")
    sys.exit(1)


def confirm(question: str) -> bool:
    """Ask a yes/no question, defaulting to 'no'."""
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def get_pypi_version() -> tuple[int, int, int]:
    """Return the latest published shpyx version on PyPI as a (major, minor, patch) tuple."""
    with urllib.request.urlopen(PYPI_URL) as response:  # noqa: S310 (trusted, hardcoded https URL)
        data = json.load(response)

    version = data["info"]["version"]
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        abort(f"Cannot parse PyPI version {version!r} as 'major.minor.patch'.")

    major, minor, patch = (int(part) for part in parts)
    return major, minor, patch


def select_next_version(current: tuple[int, int, int]) -> str:
    """Prompt the user to pick the next version relative to the current one."""
    major, minor, patch = current
    bumps = {
        "1": ("patch", f"{major}.{minor}.{patch + 1}"),
        "2": ("minor", f"{major}.{minor + 1}.0"),
        "3": ("major", f"{major + 1}.0.0"),
    }

    print(f"\nLatest version on PyPI: {major}.{minor}.{patch}")
    print("Select the next version:")
    for key, (name, version) in bumps.items():
        print(f"  {key}) {name:<5} -> {version}")

    while True:
        choice = input("Choice [1/2/3]: ").strip()
        if choice in bumps:
            return bumps[choice][1]
        print("Invalid choice, please enter 1, 2 or 3.")


def ensure_release_preconditions() -> None:
    """Verify we are on a clean, up-to-date `main` before tagging."""
    branch = shpyx.run("git rev-parse --abbrev-ref HEAD").stdout.strip()
    if branch != MAIN_BRANCH:
        abort(f"Must be on the '{MAIN_BRANCH}' branch, but currently on '{branch}'.")

    if shpyx.run("git status --porcelain").stdout.strip():
        abort("Working tree is not clean. Commit or stash your changes first.")

    print("Fetching from origin...")
    shpyx.run("git fetch origin --tags --prune", log_output=True)

    # Fast-forward only: aborts if local `main` has diverged from origin.
    shpyx.run(f"git pull --ff-only origin {MAIN_BRANCH}", log_output=True)


def tag_exists(tag: str) -> bool:
    """Return True if the tag exists locally or on origin."""
    local = shpyx.run(f"git tag --list {tag}").stdout.strip()
    remote = shpyx.run(f"git ls-remote --tags origin {tag}").stdout.strip()
    return bool(local or remote)


def delete_tag(tag: str) -> None:
    """Delete the tag both locally and on origin."""
    # Local delete may fail if the tag only exists on the remote; ignore that.
    shpyx.run(f"git tag --delete {tag}", verify_return_code=False)
    shpyx.run(f"git push --delete origin {tag}", verify_return_code=False, log_output=True)


def main() -> None:
    ensure_release_preconditions()

    next_version = select_next_version(get_pypi_version())
    tag = f"v{next_version}"

    if tag_exists(tag):
        print(f"\n⚠️  Tag {tag} already exists (a previous release may have failed).")
        if not confirm(f"Delete the existing {tag} and recreate it?"):
            abort("Aborted: tag already exists.")
        delete_tag(tag)

    if not confirm(f"\nCreate and push tag {tag} to trigger the release?"):
        abort("Aborted by user.")

    shpyx.run(f"git tag {tag}")
    shpyx.run(f"git push origin {tag}", log_output=True)

    print(f"\n✅ Pushed {tag}. The Release workflow is now running:")
    print("   https://github.com/Apakottur/shpyx/actions/workflows/release.yml")


if __name__ == "__main__":
    main()
