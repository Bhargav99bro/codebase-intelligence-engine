import pytest
from app.core.config import Settings


def test_production_config_rejects_debug_true():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        SECRET_KEY="a-very-long-and-secure-random-key-12345",
        DATABASE_URL="postgresql+asyncpg://admin:super_secret_prod_pass@db:5432/prod_db",
        BACKEND_CORS_ORIGINS=["https://cie.production.com"],
    )
    with pytest.raises(ValueError, match="DEBUG must be False in production"):
        s.validate_production_configuration()


def test_production_config_rejects_default_secret_key():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="insecure-dev-secret-key-change-in-production",
        DATABASE_URL="postgresql+asyncpg://admin:super_secret_prod_pass@db:5432/prod_db",
        BACKEND_CORS_ORIGINS=["https://cie.production.com"],
    )
    with pytest.raises(ValueError, match="SECRET_KEY must be set to a secure"):
        s.validate_production_configuration()


def test_production_config_rejects_default_db_password():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a-very-long-and-secure-random-key-12345",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres_secure_password@db:5432/codebase",
        BACKEND_CORS_ORIGINS=["https://cie.production.com"],
    )
    with pytest.raises(ValueError, match="Default database password cannot be used in production"):
        s.validate_production_configuration()


def test_production_config_rejects_wildcard_cors():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a-very-long-and-secure-random-key-12345",
        DATABASE_URL="postgresql+asyncpg://admin:super_secret_prod_pass@db:5432/prod_db",
        BACKEND_CORS_ORIGINS=["*"],
    )
    with pytest.raises(ValueError, match=r"Wildcard '\*' CORS origin is strictly forbidden in production"):
        s.validate_production_configuration()


def test_production_config_rejects_localhost_cors():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a-very-long-and-secure-random-key-12345",
        DATABASE_URL="postgresql+asyncpg://admin:super_secret_prod_pass@db:5432/prod_db",
        BACKEND_CORS_ORIGINS=["http://localhost:3000"],
    )
    with pytest.raises(ValueError, match="Localhost CORS origin 'http://localhost:3000' is forbidden"):
        s.validate_production_configuration()


def test_production_config_passes_with_valid_parameters():
    s = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="e4b3f8a912c4d5e6f708192a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c",
        DATABASE_URL="postgresql+asyncpg://prod_user:hard_random_pass_9988@db.internal:5432/cie_db",
        BACKEND_CORS_ORIGINS=["https://app.example.com", "https://dashboard.example.com"],
    )
    # Should not raise
    s.validate_production_configuration()


def test_cors_origins_parsing():
    # Comma-separated string
    s1 = Settings(BACKEND_CORS_ORIGINS="https://a.com, https://b.com")
    assert s1.BACKEND_CORS_ORIGINS == ["https://a.com", "https://b.com"]

    # JSON list string
    s2 = Settings(BACKEND_CORS_ORIGINS='["https://x.com", "https://y.com"]')
    assert s2.BACKEND_CORS_ORIGINS == ["https://x.com", "https://y.com"]


def test_resource_governance_settings():
    s = Settings()
    assert s.MAX_CONCURRENT_ANALYSES >= 1
    assert s.MAX_CLONE_PAIRS_CAP >= 1000
    assert s.MAX_CANDIDATE_BUCKET_SIZE <= 500
    assert s.STALE_JOB_THRESHOLD_MINUTES >= 5
    assert s.MAX_PAGE_SIZE <= 500


def test_redis_ssl_url_normalization_maintains_required_verification():
    import ssl
    from redis.connection import parse_url, SSLConnection
    from app.core.redis import normalize_redis_ssl_url

    # Uppercase CERT_REQUIRED must be converted to lowercase required
    raw_url = "rediss://default:supersecret@valkey.aivencloud.com:12345/0?ssl_cert_reqs=CERT_REQUIRED"
    s = Settings(REDIS_URL=raw_url)
    assert s.REDIS_URL == "rediss://default:supersecret@valkey.aivencloud.com:12345/0?ssl_cert_reqs=required"

    # Helper function normalization
    norm_url = normalize_redis_ssl_url(raw_url)
    assert norm_url == "rediss://default:supersecret@valkey.aivencloud.com:12345/0?ssl_cert_reqs=required"

    # Verify redis-py parse_url and SSLConnection accepts it without error
    parsed = parse_url(norm_url)
    assert parsed["ssl_cert_reqs"] == "required"
    conn = SSLConnection(host="valkey.aivencloud.com", port=12345, ssl_cert_reqs=parsed["ssl_cert_reqs"])
    assert conn.cert_reqs == ssl.CERT_REQUIRED


def test_database_url_cloud_normalization():
    # postgres:// to postgresql+asyncpg:// and sslmode= to ssl=
    raw_pg_url = "postgres://avnadmin:secret@pg.aivencloud.com:12345/defaultdb?sslmode=require"
    s = Settings(DATABASE_URL=raw_pg_url)
    assert s.DATABASE_URL == "postgresql+asyncpg://avnadmin:secret@pg.aivencloud.com:12345/defaultdb?ssl=require"

