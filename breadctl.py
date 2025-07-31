#!/usr/bin/env python3
"""
A tool for managing Breadbox, including creating, resetting, and removing users.
"""
import os
from pathlib import Path
from users import UserDB
import questionary
import fire

if _conf := os.environ.get('BREADBOX_CONFIG'):
    CONFIG_PATH = Path(_conf)
else:
    CONFIG_PATH = Path('./config')

db = UserDB(CONFIG_PATH / 'users.db')

class UserCLI:
    @staticmethod
    def add(username: str = None, email: str = None, password: str = None, auth_level: int = None):
        """Add a new user"""
        if not username:
            username = questionary.text("What is this user's username?").ask()
        if not username:
            exit()

        if not email:
            email = questionary.text(f"What is {username}'s email?").ask()
        if not email:
            exit()

        if not password:
            password = questionary.password(f"What is {username}'s password?").ask()
        if not password:
            exit()

        if not auth_level:
            auth_level = questionary.select(
                "Select a user type:",
                use_shortcuts=True,
                choices=[
                    questionary.Choice(
                        title='User',
                        value=1,
                        checked=True,
                        shortcut_key='1'
                    ),
                    questionary.Choice(
                        title='Contributor',
                        value=2,
                        shortcut_key='2'
                    ),
                    questionary.Choice(
                        title='Admin',
                        value=3,
                        shortcut_key='3'
                    )
                ]
            ).ask()

        if not auth_level:
            exit()

        key = db.create_user(
            username=username,
            email=email,
            password=password,
            auth_level=auth_level
        )

        print(f"\n{username}'s API key: {key}")

    @staticmethod
    def rm(username: str):
        """Remove an existing user"""
        print("Not yet implemented!")

    @staticmethod
    def reset(username: str):
        """Reset a user's API key and user ID"""
        print("Not yet implemented!")

class Pipeline:
    def __init__(self):
        self.user = UserCLI()


if __name__ == '__main__':
    fire.Fire(Pipeline)
