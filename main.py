"""
Breadbox is copyright of Akito Hoshi, 2025.

You are free to use any of the code within this project,
so long as you use it for an original purpose.
I offer no promise that any piece of this software is stable,
and I offer no warranty of any kind.

I built this software for my own personal purposes,
so there's a good chance that it may not work for your use case.

If you're aiming for a stable backend for your archive or webservice,
hire a developer. DO NOT USE AI.
"""

from uvicorn import run, __version__ as uvicorn_version
from breadbox import Breadbox, __version__ as breadbox_version
from breadbox.core.config import CONFIG_PATH

from users import UserDB

import logging

log = logging.getLogger('breadbox')

log.info(f"Using [bold yellow]{breadbox_version}[/bold yellow] as backend")
log.info(f"Using [bold yellow]uvicorn v{uvicorn_version}[/bold yellow] as server")

db = UserDB(CONFIG_PATH / 'users.db')

app = Breadbox(
    user_db_handler=db
)

if __name__ == '__main__':
    run(
        app,
        host=app.config.server.host,
        port=app.config.server.port,
        log_level="error",
        ssl_keyfile=app.config_path / 'ssl' / 'key.pem',
        ssl_certfile=app.config_path / 'ssl' / 'cert.pem',
    )
