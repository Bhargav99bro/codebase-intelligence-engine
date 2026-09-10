import ipaddress
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from app.core.config import settings


@dataclass(frozen=True)
class ValidatedRepositoryUrl:
    url: str
    owner: str
    name: str
    host: str = "github.com"


class RepositoryUrlValidationError(ValueError):
    """Raised when repository URL is invalid, unsafe, or fails SSRF checks."""
    pass


# GitHub / GitLab naming validation
# Owner: 1-39 characters, alphanumeric or single hyphens, cannot begin/end with hyphen
# Repo name: 1-100 characters, alphanumeric, hyphen, underscore, period
REPO_OWNER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
REPO_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")


def is_ip_literal_or_private(hostname: str) -> bool:
    """Checks if hostname is an IP literal or belongs to private/loopback/link-local ranges."""
    if not hostname:
        return False

    clean_host = hostname.strip("[]")

    if clean_host.lower() in ("localhost", "localhost.localdomain"):
        return True

    try:
        ip = ipaddress.ip_address(clean_host)
        # Any IP literal is rejected to prevent SSRF and internal routing
        return True
    except ValueError:
        pass

    return False


def _validate_common_url_components(raw_url: str) -> tuple[str, str, str, str]:
    """Common security validations across all supported repository git hosts."""
    if not raw_url or not isinstance(raw_url, str):
        raise RepositoryUrlValidationError("Repository URL must be a non-empty string.")

    clean_url = raw_url.strip()

    # Reject null bytes, newlines, or command injection characters
    if any(char in clean_url for char in ["\x00", "\n", "\r", ";", "&", "|", "`", "$", "<", ">", " "]):
        raise RepositoryUrlValidationError("Repository URL contains dangerous or invalid characters.")

    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise RepositoryUrlValidationError(f"Invalid URL structure: {exc}") from exc

    # Protocol check
    if parsed.scheme.lower() != "https":
        raise RepositoryUrlValidationError(
            f"Unsupported protocol: '{parsed.scheme}'. Only secure 'https://' URLs are supported."
        )

    # Credential check
    if parsed.username or parsed.password:
        raise RepositoryUrlValidationError(
            "URLs containing embedded credentials (user:pass@...) are strictly prohibited for security."
        )

    # Port check
    if parsed.port and parsed.port not in [443, None]:
        raise RepositoryUrlValidationError("Non-standard ports are not allowed for repository HTTPS URLs.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise RepositoryUrlValidationError("Repository URL is missing hostname.")

    if is_ip_literal_or_private(hostname):
        raise RepositoryUrlValidationError(
            f"IP literals and private/loopback addresses ('{hostname}') are strictly prohibited."
        )

    # Path check
    path = parsed.path.strip("/")
    if ".." in path or "\\" in path:
        raise RepositoryUrlValidationError("Path traversal sequences are strictly prohibited.")

    segments = [s for s in path.split("/") if s]
    if len(segments) != 2:
        raise RepositoryUrlValidationError(
            "Invalid repository path format. Expected format: 'https://<host>/<owner>/<repository>'."
        )

    owner, repo = segments

    if repo.endswith(".git"):
        repo = repo[:-4]

    if not REPO_OWNER_REGEX.match(owner):
        raise RepositoryUrlValidationError(
            f"Invalid GitHub owner name '{owner}'. Owner names must be alphanumeric and may contain single hyphens."
        )

    if not REPO_NAME_REGEX.match(repo) or repo in [".", ".."]:
        raise RepositoryUrlValidationError(
            f"Invalid GitHub repository name '{repo}'. Repository names must be 1-100 characters (alphanumeric, -, _, .)."
        )

    return hostname, owner, repo, path


def validate_and_normalize_github_url(raw_url: str) -> ValidatedRepositoryUrl:
    """Validates and normalizes GitHub repository URLs strictly.

    Preserves backwards compatibility with Phases 1-8 tests.
    """
    hostname, owner, repo, _ = _validate_common_url_components(raw_url)

    if hostname not in ["github.com", "www.github.com"]:
        raise RepositoryUrlValidationError(
            f"Unsupported domain: '{hostname}'. Only repositories hosted on 'github.com' are supported."
        )

    normalized_url = f"https://github.com/{owner}/{repo}"
    return ValidatedRepositoryUrl(url=normalized_url, owner=owner, name=repo, host="github.com")


def validate_and_normalize_repository_url(
    raw_url: str,
    allowed_hosts: Optional[List[str]] = None,
) -> ValidatedRepositoryUrl:
    """Validates and normalizes repository URLs across all configured allowed git hosts.

    Supports GitHub and GitLab domains with SSRF protection.
    """
    hosts = [h.lower() for h in (allowed_hosts or settings.ALLOWED_GIT_HOSTS)]
    hostname, owner, repo, _ = _validate_common_url_components(raw_url)

    if hostname not in hosts:
        raise RepositoryUrlValidationError(
            f"Unsupported domain: '{hostname}'. Allowed hosts are: {', '.join(hosts)}."
        )

    canonical_host = "gitlab.com" if "gitlab" in hostname else "github.com"
    normalized_url = f"https://{canonical_host}/{owner}/{repo}"
    return ValidatedRepositoryUrl(url=normalized_url, owner=owner, name=repo, host=canonical_host)
