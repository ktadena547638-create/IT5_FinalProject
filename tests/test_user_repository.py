"""Unit tests for UserRepository authentication and CRUD operations."""

from main import UserRepository, UserRole
from tests.conftest import DBManager


def test_user_create_authenticate_and_delete():
    """Test user creation, authentication, update, and deletion."""
    db = DBManager()
    repo = UserRepository(db)

    username = "tester"
    password = "secret"

    assert (
        repo.create_user(username, password, UserRole.MANAGER, full_name="Tester")
        is True
    )

    user = repo.authenticate(username, password)
    assert user is not None
    assert user.username == username

    assert repo.username_exists(username)

    assert repo.update_user(username, full_name="Tester Updated") is True
    fetched = repo.get_by_username(username)
    assert fetched is not None
    assert fetched.full_name == "Tester Updated"

    assert repo.delete_user(username) is True
    assert not repo.username_exists(username)
