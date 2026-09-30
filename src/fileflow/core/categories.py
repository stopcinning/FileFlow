"""Extension to category mapping.

The table is deliberately conservative. Misfiling a file is annoying in a way
that reclassifying a whole folder is not, so anything unrecognised lands in
`Other` rather than being guessed at.
"""

from __future__ import annotations

from .models import Category

_EXTENSION_MAP: dict[str, Category] = {}


def _register(category: Category, extensions: str) -> None:
    for ext in extensions.split():
        _EXTENSION_MAP[ext] = category


_register(
    Category.DOCUMENTS,
    """
    pdf doc docx odt rtf txt md markdown csv tsv xls xlsx ods ppt pptx odp
    pages numbers key epub mobi tex bib json yaml yml toml ini cfg conf
    """,
)

_register(
    Category.IMAGES,
    """
    png jpg jpeg gif webp bmp tiff tif svg heic heif avif ico raw cr2 nef
    arw dng psd xcf
    """,
)

_register(
    Category.VIDEO,
    """
    mp4 mov mkv avi wmv flv webm m4v mpg mpeg m2ts ts 3gp
    """,
)

_register(
    Category.AUDIO,
    """
    mp3 wav flac aac ogg m4a wma opus aiff aif mid
    """,
)

_register(
    Category.ARCHIVES,
    """
    zip tar gz tgz bz2 xz 7z rar zst lz4 cab iso dmg
    """,
)

_register(
    Category.CODE,
    """
    py js jsx ts tsx mjs cjs json jsonc yaml yml toml html htm css scss
    less vue svelte go rs java c h cpp hpp cc cs rb php swift kt kts scala
    sh bash zsh fish ps1 bat sql graphql gql xml lock env ini cfg conf
    dockerfile makefile cmake gradle
    """,
)

_register(
    Category.DESIGN,
    """
    fig sketch ai eps indd psd ai cdr dwg dxf figma blend obj stl
    """,
)

# Design tools overlap with Images (psd, ai). Images wins because a user
# hunting for a picture is more common than one hunting for a source file.
_EXTENSION_MAP["psd"] = Category.IMAGES


def categorise(extension: str) -> Category:
    """Map a bare extension (no dot, any case) to a category."""
    return _EXTENSION_MAP.get(extension.strip().lower().lstrip("."), Category.OTHER)


def known_extensions() -> frozenset[str]:
    return frozenset(_EXTENSION_MAP)


def table() -> list[tuple[str, Category]]:
    """Sorted mapping, for the settings UI."""
    return sorted(_EXTENSION_MAP.items(), key=lambda kv: (kv[1].value, kv[0]))
