import pytest
from app.services.url_validator import (
    RepositoryUrlValidationError,
    validate_and_normalize_github_url,
)


def test_valid_github_urls():
    valid_cases = [
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World", "https://github.com/octocat/Hello-World"),
        ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World", "https://github.com/octocat/Hello-World"),
        ("https://github.com/pallets/flask/", "pallets", "flask", "https://github.com/pallets/flask"),
        ("https://www.github.com/facebook/react.git/", "facebook", "react", "https://github.com/facebook/react"),
        ("https://github.com/user-name/repo_name.js", "user-name", "repo_name.js", "https://github.com/user-name/repo_name.js"),
        ("https://github.com/fastapi/fastapi", "fastapi", "fastapi", "https://github.com/fastapi/fastapi"),
    ]

    for raw, expected_owner, expected_name, expected_normalized in valid_cases:
        result = validate_and_normalize_github_url(raw)
        assert result.owner == expected_owner
        assert result.name == expected_name
        assert result.url == expected_normalized


def test_invalid_schemes():
    invalid_schemes = [
        "http://github.com/octocat/Hello-World",
        "git://github.com/octocat/Hello-World.git",
        "ssh://git@github.com/octocat/Hello-World.git",
        "ftp://github.com/octocat/Hello-World",
        "file:///tmp/repo",
    ]
    for url in invalid_schemes:
        with pytest.raises(RepositoryUrlValidationError, match="Unsupported protocol"):
            validate_and_normalize_github_url(url)


def test_unsupported_domains():
    unsupported_domains = [
        "https://gitlab.com/owner/repo",
        "https://bitbucket.org/owner/repo",
        "https://evil-github.com/owner/repo",
        "https://github.evil.com/owner/repo",
    ]
    for url in unsupported_domains:
        with pytest.raises(RepositoryUrlValidationError, match="Unsupported domain"):
            validate_and_normalize_github_url(url)


def test_credentials_rejected():
    credentials_urls = [
        "https://user:password@github.com/owner/repo",
        "https://token@github.com/owner/repo",
    ]
    for url in credentials_urls:
        with pytest.raises(RepositoryUrlValidationError, match="embedded credentials"):
            validate_and_normalize_github_url(url)


def test_dangerous_characters_and_command_injection():
    dangerous_urls = [
        "https://github.com/owner/repo; rm -rf /",
        "https://github.com/owner/repo && echo pwned",
        "https://github.com/owner/repo|cat /etc/passwd",
        "https://github.com/owner/repo`reboot`",
        "https://github.com/owner/repo$(whoami)",
        "https://github.com/owner/repo\x00extra",
    ]
    for url in dangerous_urls:
        with pytest.raises(RepositoryUrlValidationError, match="dangerous or invalid"):
            validate_and_normalize_github_url(url)


def test_path_traversal():
    traversal_urls = [
        "https://github.com/owner/../repo",
        "https://github.com/owner/..\\repo",
        "https://github.com/../owner/repo",
    ]
    for url in traversal_urls:
        with pytest.raises(RepositoryUrlValidationError, match="Path traversal"):
            validate_and_normalize_github_url(url)


def test_invalid_path_segments():
    invalid_paths = [
        "https://github.com",
        "https://github.com/",
        "https://github.com/owner",
        "https://github.com/owner/repo/subpath",
        "https://github.com/owner/repo/blob/main/file.py",
    ]
    for url in invalid_paths:
        with pytest.raises(RepositoryUrlValidationError, match="Invalid repository path format"):
            validate_and_normalize_github_url(url)


def test_invalid_names():
    invalid_names = [
        ("https://github.com/-badowner/repo", "Invalid GitHub owner name"),
        ("https://github.com/badowner-/repo", "Invalid GitHub owner name"),
        ("https://github.com/owner/repo*name", "Invalid GitHub repository name"),
        ("https://github.com/owner/..", "Path traversal sequences are strictly prohibited"),
    ]
    for url, err_snippet in invalid_names:
        with pytest.raises(RepositoryUrlValidationError, match=err_snippet):
            validate_and_normalize_github_url(url)
