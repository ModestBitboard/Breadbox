"""
Operations related to the archive containing Games ROMs and ISOs.
"""

from pydantic import BaseModel, Field
from typing import Optional

from breadbox import ArchiveRouter
from breadbox.core.responses import respond

class GameExternalInfo(BaseModel):
    wikipedia: Optional[str] = Field(
        default=None,
        description='Link to the game on Wikipedia',
        examples=['https://en.wikipedia.org/wiki/Super_Mario_Galaxy_2']
    )
    igdb: Optional[str] = Field(
        default=None,
        description='Link to the game on IGDB',
        examples=['https://www.igdb.com/games/super-mario-galaxy-2']
    )

class GameModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description='Title of the game',
        examples=['Super Mario Galaxy 2']
    )
    platform: Optional[str] = Field(
        default=None,
        description='A tag for what platform the game was released on',
        examples=['wii']
    )
    rating: Optional[str] = Field(
        default=None,
        description='ESRB rating of the game',
        examples=['E']
    )
    external: Optional[GameExternalInfo] = Field(
        default=None,
        description='Links to the game on other websites'
    )


router = ArchiveRouter(
    model=GameModel,
    name='Games',
)

@router.image('/thumbnail')
def game_thumbnail():
    """Thumbnail of the game."""
    return 'thumbnail.jpg'

@router.image('/logo')
def game_logo():
    """Logo of the game."""
    return 'logo.png'

@router.media('/files/{filename}', overwrite_protection=True)
def game_file(filename: str):
    """ISO file for the Linux distro release"""
    return filename

# noinspection PyShadowingBuiltins
@router.get('/{id}/files')
def list_game_files(id: int):
    """
    List all available files of the Linux distro release
    """

    if not router.archive.check_item(id):
        return respond('not_in_archive')

    # List files
    files = []

    root_path = (router.archive.path / str(id) / 'media').resolve()

    if root_path.is_dir():
        for file in root_path.iterdir():
            if file.resolve().is_file():
                files.append(file.name)

        files.sort()

    return {
        "files": files
    }
