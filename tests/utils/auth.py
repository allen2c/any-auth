import pytest

from any_auth.utils.auth import is_valid_password


@pytest.mark.parametrize(
    "password, valid",
    [
        ("SecureP@ssw0rd!", True),  # valid
        ("My_Password123#", True),  # valid
        ("password", False),  # lacks uppercase, digits, special chars
        ("Password1", False),  # lacks special characters
        ("Password!", False),  # lacks digits
        ("P@ssw0rd", True),  # exactly 8 characters
        ("ThisIsAVeryLongPassword123!@#", True),  # within 64 characters
        ("Short1!", False),  # less than 8 characters
        ("NoSpecialChar123", False),  # lacks special characters
        ("😊SecureP@ssw0rd!", False),  # contains an emoji
        ("ValidPassw0rd$", True),  # valid
    ],
)
def test_is_valid_password(password, valid):
    assert is_valid_password(password) == valid
