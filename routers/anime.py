"""
Operations related to the archive containing Anime OVAs, Movies, Seasons, etc.
"""

from pydantic import BaseModel, Field
from typing import Optional

from breadbox import ArchiveRouter
from breadbox.core.responses import respond

class AnimeExternalInfo(BaseModel):
    myanimelist: Optional[str] = Field(
        default=None,
        description='Link to the anime on MyAnimeList.net',
        examples=['https://myanimelist.net/anime/38759']
    )
    jikan: Optional[str] = Field(
        default=None,
        description='Link to the anime on Jikan.moe (An unofficial MyAnimeList API)',
        examples=['https://api.jikan.moe/v4/anime/38759']
    )
    anilist: Optional[str] = Field(
        default=None,
        description='Link to the anime on AniList.co',
        examples=['https://anilist.co/anime/105914']
    )

class AnimeTorrentInfo(BaseModel):
    magnet: Optional[str] = Field(
        default=None,
        description='Magnet link of the torrent this media is from',
        examples=['magnet:?xt=urn:btih:692aab53b69012278079b5983c75daff8b8c444f...']
    )
    url: Optional[str] = Field(
        default=None,
        description='Link to torrent page (Nyaa.si usually)',
        examples=['https://nyaa.si/view/1557245']
    )

class AnimeModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description='Title of the anime',
        examples=['The Helpful Fox Senko-san']
    )
    audio: Optional[list[str]] = Field(
        default=None,
        description='List of available dubbed languages',
        examples=[['japanese', 'english']]
    )
    subtitles: Optional[list[str]] = Field(
        default=None,
        description='List of available subtitled languages',
        examples=[['english']]
    )
    external: Optional[AnimeExternalInfo] = Field(
        default=None,
        description='Links to the anime on other websites'
    )
    torrent: Optional[AnimeTorrentInfo] = Field(
        default=None,
        description='Information about the torrent the media is from'
    )


router = ArchiveRouter(
    model=AnimeModel,
    name='Anime',
)

@router.image('/thumbnail')
def anime_thumbnail():
    """Thumbnail of the anime"""
    return 'thumbnail.jpg'

@router.image('/banner')
def anime_banner():
    """Banner of the anime"""
    return 'banner.png'

@router.image('/logo')
def anime_logo():
    """Logo of the anime"""
    return 'logo.png'

@router.image('/media/{media}/thumbnail')
def anime_media_thumbnail(media: str):
    """The thumbnail for an episode or piece of bonus content of the anime"""
    if media.isnumeric():
        return 'EP-%02d.png' % int(media)
    else:
        return '%s.png' % media.upper()

@router.media('/media/{media}', overwrite_protection=True)
def anime_media(media: str):
    """Episode or bonus content of the anime"""
    if media.isnumeric():
        return '%02d.mkv' % int(media)
    else:
        return 'bonus/%s.mkv' % media.upper()

# noinspection PyShadowingBuiltins
@router.get('/{id}/media')
def list_anime_media(id: int):
    """
    List all available media of an anime, including episodes and bonus content
    """

    if not router.archive.check_item(id):
        return respond('not_in_archive')

    # List episodes
    episodes = []
    bonus = []

    root_path = (router.archive.path / str(id) / 'media').resolve()

    if root_path.is_dir():
        for file in root_path.iterdir():
            if file.suffix != '.mkv':
                continue
            if not file.stem.isnumeric():
                continue
            if file.resolve().is_file():
                episodes.append(int(file.stem))

        episodes.sort()

        # List any bonus content
        bonus_dir = (root_path / 'bonus').resolve()

        if bonus_dir.is_dir():
            for file in bonus_dir.iterdir():
                if file.stem.startswith(('.', '_')):
                    continue
                if not file.stem.isupper():
                    continue
                if file.resolve().is_file():
                    bonus.append(file.stem)

            bonus.sort()

    return {
        "episodes": episodes,
        "bonus": bonus
    }
