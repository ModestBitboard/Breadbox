"""
Operations related to the archive containing Games ROMs and ISOs.
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

from breadbox import ArchiveRouter

class GameExternalInfo(BaseModel):
    wikipedia: Optional[str] = Field(
        default=None,
        description='Link to Wikipedia',
        examples=['https://en.wikipedia.org/wiki/Super_Mario_Galaxy_2']
    )

class GameModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description='Title of the game',
        examples=['Super Mario Galaxy 2']
    )
    platform: Optional[str] = Field(
        default=None,
        description='What platform the game was released on',
        examples=['Wii']
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

@router.image('/banner')
def game_banner():
    """Banner of the game."""
    return 'banner.png'

@router.image('/logo')
def game_logo():
    """Logo of the game."""
    return 'logo.png'

@router.media('/zip')
def game_file():
    """7z file containing the game file."""
    return 'game.7z'
