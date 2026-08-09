from src.core.security import AuthenticatedUser


def test_full_access_email_is_case_insensitive_and_exact():
    assert AuthenticatedUser("admin", " ADMIN@gmail.com ").has_full_access
    assert not AuthenticatedUser("other", "admin+other@gmail.com").has_full_access
    assert not AuthenticatedUser("anonymous").has_full_access
