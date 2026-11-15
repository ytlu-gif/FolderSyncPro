"""Read-only update checks for public GitHub Releases."""

from dataclasses import dataclass
import json
import re
from urllib.request import Request, urlopen


REPOSITORY = "ytlu-gif/FolderSyncPro"
RELEASES_API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
REQUEST_TIMEOUT_SECONDS = 4

_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?$"
)
_PRE_RELEASE_RANK = {"alpha": 0, "beta": 1, "rc": 2}


@dataclass(frozen=True)
class ReleaseInfo:
    """The small, user-facing part of a GitHub release response."""

    tag_name: str
    name: str
    html_url: str


def version_key(value: str):
    """Return a sortable key for the project's SemVer-style versions."""

    match = _VERSION_PATTERN.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Unsupported version: {value!r}")

    base = (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )
    pre = match.group("pre")

    # A final release sorts after alpha, beta, and rc for the same base version.
    if not pre:
        return base + (1, 0, 0)

    parts = pre.lower().split(".")
    rank = _PRE_RELEASE_RANK.get(parts[0], -1)
    number = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return base + (0, rank, number)


def _release_info(item):
    if item.get("draft"):
        return None

    tag_name = str(item.get("tag_name", "")).strip()
    try:
        version_key(tag_name)
    except ValueError:
        return None

    html_url = str(item.get("html_url", "")).strip()
    if not html_url:
        return None

    return ReleaseInfo(
        tag_name=tag_name,
        name=str(item.get("name") or tag_name),
        html_url=html_url,
    )


def find_newer_release(current_version: str, releases):
    """Return the newest published release newer than ``current_version``."""

    current_key = version_key(current_version)
    candidates = []

    for item in releases:
        release = _release_info(item)
        if release is None:
            continue
        if version_key(release.tag_name) > current_key:
            candidates.append(release)

    if not candidates:
        return None

    return max(candidates, key=lambda release: version_key(release.tag_name))


def _fetch_releases(timeout):
    request = Request(
        RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "FolderSyncPro-update-checker",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        raise ValueError("GitHub returned an unexpected releases response")

    return payload


def get_latest_release(timeout=REQUEST_TIMEOUT_SECONDS):
    """Return the newest published release, including the current version."""

    releases = [
        release
        for item in _fetch_releases(timeout)
        if (release := _release_info(item)) is not None
    ]
    if not releases:
        return None

    return max(releases, key=lambda release: version_key(release.tag_name))


def check_for_update(current_version: str, timeout=REQUEST_TIMEOUT_SECONDS):
    """Fetch public release metadata and return a newer release, if available."""

    latest = get_latest_release(timeout)
    if latest is None or version_key(latest.tag_name) <= version_key(current_version):
        return None

    return latest
