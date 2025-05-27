from fastapi.responses import FileResponse
from fastapi import UploadFile, APIRouter

from pydantic import BaseModel

from typing import Callable, Type
from pathlib import Path

import functools
import inspect
import aiofiles
import mimetypes
import time
import string
import json

from breadbox.core.config import Config
from breadbox.core.responses import respond
from breadbox.core.security import rate_limiter

# Constant showing a list of valid characters for a name
NAME_CHARS = string.ascii_letters + string.digits + '_-'


# noinspection PyShadowingBuiltins
class ArchiveRouter(APIRouter):
    def __init__(self, model: Type[BaseModel], name: str, auto: bool = True, *args, **kwargs):
        """
        Special router for making archives. Automatically generates endpoints.
        :param model: Pydantic model of the crumb.json file
        :param name: The name of the archive.
        :param auto: If true, generates a bunch of endpoints automatically.
        """
        super().__init__(*args, **kwargs)

        if not all(c in NAME_CHARS for c in name):
            raise ValueError("'name' can only contain these characters: " + NAME_CHARS)

        self.model = model
        self.name = name

        if not Config.archives.get(name):
            raise LookupError("You need to specify an archive path in the config.")

        self.archive = ArchiveHandler(self.model, Config.archives.get(name))

        if auto:
            self._generate()

    def _generate(self):
        """Automagically generates endpoints for the archive"""
        model = self.model

        class ArchiveSize(BaseModel):
            size: int

        async def list_ids() -> list[int]:
            """List all IDs within the archive"""
            return self.archive.list_items()

        self.add_api_route(
            '/',
            list_ids,
            methods=['GET'],
            name=self.name.lower() + '_list_ids'
        )

        def all_info() -> dict[str, model]:
            """Get a dictionary of all the info within the archive"""
            response = {}
            for _id in self.archive.list_items():
                response[str(_id)] = self.archive.get_item_info(_id)
            return response

        self.add_api_route(
            '/all',
            all_info,
            methods=['GET'],
            name=self.name.lower() + '_all_info'
        )

        def size() -> ArchiveSize:
            """Get the amount of items in the archive"""
            return ArchiveSize(size=len(self.archive.list_items()))

        self.add_api_route(
            '/size',
            size,
            methods=['GET'],
            name=self.name.lower() + '_count'
        )

        async def info(id: int) -> model:
            """Get info from a crumb"""
            try:
                return self.model.model_validate(self.archive.get_item_info(id))
            except FileNotFoundError:
                return respond('not_in_archive')

        self.add_api_route(
            '/{id}',
            info,
            methods=['GET'],
            name=self.name.lower() + '_info'
        )

        def update_info(id: int, data: model):
            """Update the item's metadata or create a new item if it doesn't exist yet."""
            try:
                existing_data = self.archive.get_item_info(id)
                final_data = existing_data | data.model_dump()
                self.archive.set_item_info(id, final_data)
                return respond('resource_updated')

            except FileNotFoundError:
                self.archive.set_item_info(id, data.model_dump())
                return respond('resource_created')

        self.add_api_route(
            '/{id}',
            update_info,
            methods=['PATCH'],
            name='update_' + self.name.lower() + '_info'
        )

    def add_file(self, path: str, branch: str | Path):
        """
        Creates read-write endpoints for a file inside an item.
        :param path: URL path relative to the item path
        :param branch: Directory within the item to serve files from. Usually `media` or `images`.
        """
        if path.startswith('/'):
            path = path.removeprefix('/')

        def wrapper(func: Callable[..., str]):
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            for i, param in enumerate(params):
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    break
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    break
            else:
                i = len(params)

            id_param = inspect.Parameter(
                'id',
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=int
            )
            params.insert(i, id_param)
            get_sig = sig.replace(parameters=params)

            upload_file_param = inspect.Parameter(
                'file',
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=UploadFile
            )

            params.insert(i+1, upload_file_param)
            upload_sig = sig.replace(parameters=params)

            @functools.wraps(func)
            async def _get_file(*args, **kwargs) -> FileResponse:
                bound = get_sig.bind(*args, **kwargs)
                bound.apply_defaults()
                id: int = bound.arguments['id']
                del bound.arguments['id']

                filename = func(*bound.args, **bound.kwargs)

                if (_f := filename.split('.'))[0] == self.name:
                    nickname = f'{self.name}-{str(id)}.{_f[-1]}'
                else:
                    nickname = f'{self.name}-{str(id)}-{filename}'

                _path = self.archive.path / str(id) / branch / filename

                _path = _path.resolve()  # Adds support for symlinks

                if _path.is_file():
                    return FileResponse(
                        _path,
                        filename=nickname
                    )
                else:
                    return respond('not_in_archive')

            @functools.wraps(func)
            async def _upload_file(*args, **kwargs):
                bound = upload_sig.bind(*args, **kwargs)
                bound.apply_defaults()
                file: UploadFile = bound.arguments['file']
                id: int = bound.arguments['id']
                del bound.arguments['file']
                del bound.arguments['id']

                filename = func(*bound.args, **bound.kwargs)

                media_type = mimetypes.guess_type(filename)[0]

                if file.content_type != media_type:
                    return respond('wrong_content_type', expected_mimetype=media_type)

                if not self.archive.check_item(id):
                    raise respond('not_in_archive')

                branch_path = self.archive.path / str(id) / branch

                if not branch_path.is_dir():
                    branch_path.mkdir()

                _path = branch_path / filename

                _st = time.time()

                # https://stackoverflow.com/a/63581187
                async with aiofiles.open(_path, 'wb') as out_file:
                    while content := await file.read(1024):
                        await out_file.write(content)

                _et = time.time()

                return respond(
                    'upload_succeeded',
                    file_size=file.size,
                    elapsed_time=_et - _st
                )

            _get_file.__signature__ = get_sig
            _upload_file.__signature__ = upload_sig

            _get_file.__name__ = 'get_' + func.__name__
            _upload_file.__name__ = 'upload_' + func.__name__

            rate_limiter.exempt(_get_file)

            self.add_api_route(
                '/{id}/' + path,
                _get_file,
                methods=['GET'],
            )

            self.add_api_route(
                '/{id}/' + path,
                _upload_file,
                methods=['PUT'],
            )

        return wrapper

    def image(self, path: str):
        """
        Decorator that creates read-write endpoints for an image inside an item
        :param path: Path to the image file relative to the item's `images` directory
        """
        return self.add_file(path, 'images')

    def media(self, path: str):
        """
        Decorator that creates read-write endpoints for a media file inside an item
        :param path: URL to bind functions to. Will be prefixed with `/{id}/`.
        """
        return self.add_file(path, 'media')


# noinspection PyShadowingBuiltins
class ArchiveHandler:
    def __init__(self, model: Type[BaseModel], path: str | Path):
        """
        An easy interface for interacting with archives
        """
        self.model = model
        self.path = Path(path)

        if not self.path.exists():
            self.path.mkdir()

        elif self.path.is_file():
            raise NotADirectoryError(
                "Specified archive directory is a file. Please delete it or change your archive path."
            )

    def list_items(self):
        """
        List all the items in the archive
        """
        crumbs = [
            int(_p.name) for _p in self.path.iterdir()
            if _p.is_dir() and _p.name.isnumeric() and (_p / 'crumb.json').is_file()
        ]

        crumbs.sort()

        return crumbs

    def check_item(self, id: int) -> bool:
        """
        Check if an item is in the archive
        """
        return (self.path / str(id) / 'crumb.json').is_file()

    def get_item_info(self, id: int) -> dict:
        """
        Get information on an item in the archive
        """
        with open(self.path / str(id) / 'crumb.json', 'r') as f:
            return json.load(f)

    def set_item_info(self, id: int, data: dict):
        """
        Set information on an item in the archive
        """
        if not (item_path := self.path / str(id)).exists():
            item_path.mkdir()
        with open(self.path / str(id) / 'crumb.json', 'w') as f:
            json.dump(data, f, indent=2)

