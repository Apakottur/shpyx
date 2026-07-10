#!/usr/bin/env python
"""
Create a new shpyx release.
"""

import sys

import httpx

import shpyx

_PYPI_URL = "https://pypi.org/pypi/shpyx/json"
_MAIN_BRANCH = "main"


def _abort(message: str) -> None:
    print(f"\n❌ {message}")
    sys.exit(1)


def _confirm(question: str) -> None:
    user_input = input(f"{question} [y/N] ").strip().lower()
    if user_input != "y":
        _abort("Aborted by user.")


def main() -> None:
    # Verify we are on a clean, up-to-date `main` before tagging.
    branch = shpyx.run("git rev-parse --abbrev-ref HEAD").stdout.strip()
    if branch != _MAIN_BRANCH:
        _abort(f"Must be on the '{_MAIN_BRANCH}' branch, but currently on '{branch}'.")
    if shpyx.run("git status --porcelain").stdout.strip():
        _abort("Working tree is not clean. Commit or stash your changes first.")

    # Fetch and fast-forward to origin/main.
    print("Fetching from origin...")
    shpyx.run("git pull", log_output=True)

    # Look up the latest published version on PyPI.
    pypi_response = httpx.get(_PYPI_URL)
    pypi_response.raise_for_status()
    version = pypi_response.json()["info"]["version"]
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        _abort(f"Cannot parse PyPI version {version!r} as 'major.minor.patch'.")
    major, minor, patch = (int(part) for part in parts)

    # Let the user pick the next version.
    bumps = {
        "1": ("patch", f"{major}.{minor}.{patch + 1}"),
        "2": ("minor", f"{major}.{minor + 1}.0"),
        "3": ("major", f"{major + 1}.0.0"),
    }
    print(f"\nLatest version on PyPI: {major}.{minor}.{patch}")
    print("Select the next version:")
    for key, (name, next_version) in bumps.items():
        print(f"  {key}) {name:<5} -> {next_version}")
    while (choice := input("Choice [1/2/3]: ").strip()) not in bumps:
        print("Invalid choice, please enter 1, 2 or 3.")
    tag = f"v{bumps[choice][1]}"

    # Handle a pre-existing tag (e.g. from a release run that failed after tagging).
    local = shpyx.run(f"git tag --list {tag}").stdout.strip()
    remote = shpyx.run(f"git ls-remote --tags origin {tag}").stdout.strip()
    if local or remote:
        print(f"\n⚠️  Tag {tag} already exists (a previous release may have failed).")
        _confirm(f"Delete the existing {tag} and recreate it?")
        # Local delete may fail if the tag only exists on the remote; ignore that.
        shpyx.run(f"git tag --delete {tag}", verify_return_code=False)
        shpyx.run(f"git push --delete origin {tag}", verify_return_code=False)

    # Create and push the tag.
    _confirm(f"\nCreate and push tag {tag} to trigger the release?")
    shpyx.run(f"git tag {tag}")
    shpyx.run(f"git push origin {tag}")

    # Print the release URL.
    print(f"\n✅ Pushed {tag}. The Release workflow is now running:")
    print("   https://github.com/Apakottur/shpyx/actions/workflows/release.yml")


if __name__ == "__main__":
    main()
