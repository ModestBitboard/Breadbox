"""
Operations related to the archive containing Manga.
"""

from pydantic import BaseModel, Field
from typing import Optional
from packaging.version import Version

from breadbox import ArchiveRouter
from breadbox.core.responses import respond

class MangaExternalInfo(BaseModel):
    myanimelist: Optional[str] = Field(
        default=None,
        description='Link to the manga on MyAnimeList.net',
        examples=['https://myanimelist.net/manga/111276']
    )
    jikan: Optional[str] = Field(
        default=None,
        description='Link to the manga on Jikan.moe (An unofficial MyAnimeList API)',
        examples=['https://api.jikan.moe/v4/manga/111276']
    )
    anilist: Optional[str] = Field(
        default=None,
        description='Link to the manga on AniList.co',
        examples=['https://anilist.co/manga/100584']
    )
    mangadex: Optional[str] = Field(
        default=None,
        description='Link to the manga on MangaDex.org',
        examples=['https://mangadex.org/title/c26269c7-0f5d-4966-8cd5-b79acb86fb7a']
    )

class MangaModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description='Title of the manga',
        examples=['The Helpful Fox Senko-san']
    )
    language: Optional[str] = Field(
        default=None,
        description="The language the manga is available in",
        examples=['english']
    )
    external: Optional[MangaExternalInfo] = Field(
        default=None,
        description='Links to the manga on other websites'
    )


router = ArchiveRouter(
    model=MangaModel,
    name='Manga',
)

@router.image('/thumbnail')
def manga_thumbnail():
    """Thumbnail of the manga"""
    return 'thumbnail.jpg'

@router.media('/chapters/{chapter}', overwrite_protection=True)
def manga_chapters(chapter: str):
    """Chapter of the manga"""
    return '%s.cbz' % chapter

# noinspection PyShadowingBuiltins
@router.get('/{id}/chapters')
def list_manga_chapters(id: int):
    """
    List all available chapters of the manga
    """

    if not router.archive.check_item(id):
        return respond('not_in_archive')

    # List files
    chapters = []

    root_path = (router.archive.path / str(id) / 'media').resolve()

    if root_path.is_dir():
        for file in root_path.iterdir():
            if file.suffix != '.cbz':
                continue

            if file.resolve().is_file():
                chapters.append(file.stem)

        chapters.sort(key=Version)

    return {
        "chapters": chapters
    }
