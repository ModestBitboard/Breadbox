"""
A simple users database for usage with Breadbox
"""

from sqlmodel import Field, SQLModel, create_engine, Session, select
from pydantic import EmailStr
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pathlib import Path
import hashlib
import secrets

hasher = PasswordHasher()

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    email: EmailStr
    password: str
    api_key: str = Field(unique=True)
    user_id: int = Field(unique=True)
    auth_level: int = Field(default=1)

class UserDB:
    def __init__(self, db_path: str | Path):
        if isinstance(db_path, Path):
            db_path = str(db_path)

        self.engine = create_engine("sqlite:///" + db_path)
        SQLModel.metadata.create_all(self.engine)

    @staticmethod
    def derive_user_id(api_key: str):
        """
        The user ID is derived from a SHA256 hash of the first 8 characters of the API key
        :param api_key:
        :return:
        """
        return int(
            hashlib.sha256(
                api_key.encode()[:8]
            ).hexdigest()[:10],
            base=16
        )

    def create_user(self, username: str, email: str, password: str, auth_level: int) -> str:
        """
        Add a new user to the database.
        :param username:
        :param email:
        :param password:
        :param auth_level: The user's authentication level. 1=user, 2=contributor, 3=admin
        :return: The user's API key
        """

        api_key = secrets.token_urlsafe(28)
        api_key_id = self.derive_user_id(api_key)

        with Session(self.engine) as session:
            session.add(User(
                name=username,
                email=email,
                password=hasher.hash(password),
                api_key=hasher.hash(api_key),
                user_id=api_key_id,
                auth_level=auth_level
            ))
            session.commit()

        return api_key

    def check_key(self, api_key: str):
        """
        Take an API key then check if it's valid.
        If true, return a username and auth level.
        If false, return nothing.
        :param api_key: The API key
        :return: Either (username, auth level) if the API key is valid, or (None, None) if it isn't.
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.user_id == self.derive_user_id(api_key))
            # noinspection PyTypeChecker
            user = session.exec(statement).first()

        if not user:
            return None, None

        try:
            hasher.verify(user.api_key, api_key)
            return user.name, user.auth_level
        except VerifyMismatchError:
            return None, None


if __name__ == '__main__':
    # An example for quickly creating a test user.

    db = UserDB('config/users.db')
    key = db.create_user(
        username="mihari",
        email="oyama.mihari@example.com",
        password="correct horse battery staple",
        auth_level=2
    )

    print("API key:", key)

