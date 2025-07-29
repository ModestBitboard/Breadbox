"""
Operations related to the archive containing Linux ISOs.
"""

from pydantic import BaseModel, Field
from typing import Optional

from breadbox import ArchiveRouter
from breadbox.core.responses import respond

class LinuxTorrentInfo(BaseModel):
    magnet: Optional[str] = Field(
        default=None,
        description='Magnet link of the torrent this ISO is from',
        examples=['magnet:?xt=urn:btih:611f70899d4e1d6a9c39cfc925f103dfef630328...']
    )
    file: Optional[str] = Field(
        default=None,
        description='Link to .torrent file',
        examples=['https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-live-server-amd64.iso.torrent']
    )

class LinuxModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description='Title of the Linux ISO',
        examples=['Ubuntu 24.04.2']
    )
    identifier: Optional[str] = Field(
        default=None,
        description="The distro's identifier",
        examples=['ubuntu']
    )
    version: Optional[str] = Field(
        default=None,
        description='The release version',
        examples=['24.04.2']
    )
    torrent: Optional[LinuxTorrentInfo] = Field(
        default=None,
        description='Information about the torrent the ISO is from'
    )


router = ArchiveRouter(
    model=LinuxModel,
    name='Linux',
)

@router.media('/files/{filename}', overwrite_protection=True)
def linux_file(filename: str):
    """ISO file for the Linux distro release"""
    if not filename.endswith('.iso'):
        filename += '.iso'
    return filename

# noinspection PyShadowingBuiltins
@router.get('/{id}/files')
def list_linux_files(id: int):
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
            if file.suffix != '.iso':
                continue

            if file.resolve().is_file():
                files.append(file.name)

        files.sort()

    return {
        "files": files
    }
