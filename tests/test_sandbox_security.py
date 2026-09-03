from cloud.sandbox_security import bounded_redacted_text, redact_sensitive_text


def test_redaction_removes_common_credential_shapes():
    value = (
        "https://user:password@example.test/simple?token=query-secret "
        "Authorization: Bearer header-secret API_KEY=assignment-secret"
    )

    redacted = redact_sensitive_text(value)

    for secret in ("user", "password", "query-secret", "header-secret", "assignment-secret"):
        assert secret not in redacted
    assert "example.test/simple" in redacted
    assert redacted.count("<redacted>") >= 3


def test_explicit_package_index_secret_is_removed():
    secret = "https://index-user:index-password@packages.example/simple"

    redacted = redact_sensitive_text(f"resolver failed for {secret}", secrets=(secret,))

    assert secret not in redacted
    assert redacted == "resolver failed for <redacted>"


def test_bounded_diagnostic_limits_utf8_after_redaction():
    result = bounded_redacted_text("TOKEN=secret-value\n" + "ộ" * 1000, 128)

    assert "secret-value" not in result
    assert len(result.encode("utf-8")) <= 128
    assert "truncated" in result
