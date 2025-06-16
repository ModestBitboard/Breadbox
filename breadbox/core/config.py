"""
Tools for managing config files.

Ideally I'd just have this module search for a config file in /usr/share/breadbox
and then create a config file if one is not present, but because I want to
run breadbox in a container AND I want to test it without creating files in /usr/share
you're going to have to bear witness to a very concerning usage of environment variables.
"""

from pathlib import Path
from pydantic import BaseModel
import toml
import os

import logging

from typing import Literal, Optional

# Grab the logger
log = logging.getLogger('breadbox')

# Helpful types
groups = Literal['everyone', 'users', 'contributors', 'admin', 'nobody']

# Pydantic model containing all the settings and modifiable values.
class _App(BaseModel):
    name: str = "Breadbox"
    flair: Optional[str] = "\U0001F4E6"
    version: str = "1.0"
    author: str = "Akito Hoshi"
    summary: str = "An archive of anime, games, and Linux ISOs."
    show_watermark: bool = False

class _Server(BaseModel):
    port: int = 8080
    host: str = '0.0.0.0'

class _RateLimits(BaseModel):
    enabled: bool = True
    rules: tuple = ("3/second", "20/minute")

class _SignedUrls(BaseModel):
    enabled: bool = True
    duration: int = 720

class _Permissions(BaseModel):
    read: groups = 'users'
    write: groups = 'contributors'
    delete: groups = 'admin'
    other: groups = 'everyone'

class _Advanced(BaseModel):
    cache_openapi: bool = True
    integrated_docs: bool = True
    log_level: str = 'INFO'
    read_only: bool = False
    protected_prefixes: tuple = ('/archive',)
    auth_header: Optional[str] = "X-API-KEY"
    auth_cookie: Optional[str] = ""

class ConfigModel(BaseModel):
    app: _App = _App()
    server: _Server = _Server()
    rate_limits: _RateLimits = _RateLimits()
    signed_urls: _SignedUrls = _SignedUrls()
    permissions: _Permissions = _Permissions()
    archives: dict[str, Path] = {}
    advanced: _Advanced = _Advanced()


# Some helper functions for managing our config.toml file
def config_load() -> ConfigModel:
    """
    Load the config.toml file to a ConfigModel
    """
    with open(CONFIG_PATH / 'config.toml', mode='r', encoding='UTF-8') as fp:
        _config = toml.load(fp)

    return ConfigModel.model_validate(_config)

def config_dump(obj: ConfigModel):
    """
    Dump a ConfigModel to the config.toml file
    """
    with open(CONFIG_PATH / 'config.toml', mode='w', encoding='UTF-8') as fp:
        toml.dump(
            obj.model_dump(mode='python'), fp,
            encoder=toml.TomlPathlibEncoder()
        )


# Check environment variables for the Breadbox config path...
if _conf := os.environ.get('BREADBOX_CONFIG'):
    CONFIG_PATH = Path(_conf)
else:
    # ...if it isn't found, set it to default and slap the dev on the wrist.
    CONFIG_PATH = Path('./config')
    log.warning("BREADBOX_CONFIG has not been set. Defaulting to ./config")

log.info('Loading config from %s' % CONFIG_PATH.absolute())

# Check if the config path exists
if not CONFIG_PATH.exists():
    log.warning("Config files don't exist. They will be generated.")
    CONFIG_PATH.mkdir()

# Check if, for some godforsaken reason, the config path leads to a file.
if CONFIG_PATH.is_file():
    raise NotADirectoryError(
        "Specified config directory is a file. Please delete it or change your config path."
    )

# Check if the files within the config path are already there
config_toml = CONFIG_PATH / 'config.toml'

if not config_toml.is_file():
    with open(config_toml, mode='w', encoding='UTF-8') as f:
        config_dump(ConfigModel())

    log.info("Config files have been generated. Please make the necessary changes before running again.")
    exit()


# Create the config model object
Config = config_load()

# Set log level now that config is accessible
log.setLevel(Config.advanced.log_level)

# Prevent any devs from importing anything confusing and irrelevant
__all__ = [
    'CONFIG_PATH',
    'Config',
    'ConfigModel',
    'config_load',
    'config_dump'
]
