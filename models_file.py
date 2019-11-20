import attr
from typing import List, Dict, Optional, TypeVar, Union


@attr.s
class UserLinks(object):
    fa: Optional[str] = attr.ib(default=None)
    weasyl: Optional[str] = attr.ib(default=None)


@attr.s
class ImageLinks(object):
    fa: Optional[int] = attr.ib(default=None)
    weasyl: Optional[str] = attr.ib(default=None)


@attr.s
class ImageSequence(object):
    first: Optional[str] = attr.ib(default=None)
    next: Optional[str] = attr.ib(default=None)


@attr.s
class Artist(object):
    name: str = attr.ib()
    links: Optional[UserLinks] = attr.ib(default=None)


T = TypeVar("T")


def make_list(x: Union[List[T], T]) -> List[T]:
    if isinstance(x, list) and not isinstance(x, str):
        return x
    return [x]


@attr.s
class Submission(object):
    filename: str = attr.ib()
    title: str = attr.ib()
    slug: str = attr.ib()
    date: int = attr.ib()
    tags: List[str] = attr.ib()
    characters = attr.ib(
        converter=make_list
    )  # typing doesn't play nice with make_list :(
    description: Optional[str] = attr.ib(default=None)
    visibility: Optional[str] = attr.ib(default=None)
    lockout: Optional[str] = attr.ib(default=None)
    sequence: Optional[ImageSequence] = attr.ib(default=None)
    my_links: Optional[ImageLinks] = attr.ib(default=None)
    artist_links: Optional[ImageLinks] = attr.ib(default=None)


@attr.s
class ArtistFile(object):
    artist: Artist = attr.ib()
    files: List[Submission] = attr.ib()


@attr.s
class CharacterSpeciesSubform(object):
    refsheet: Optional[Dict[str, str]] = attr.ib(default=None)
    description: Optional[str] = attr.ib(default=None)


@attr.s
class CharacterSpecies(CharacterSpeciesSubform):
    subforms: Optional[Dict[str, Optional[CharacterSpeciesSubform]]] = attr.ib(
        default=None
    )


@attr.s
class Character(object):
    name: str = attr.ib()
    species: Dict[str, Optional[CharacterSpecies]] = attr.ib()
    description: Optional[str] = attr.ib(default=None)
    owner: Optional[str] = attr.ib(default=None)
    root: Optional[bool] = attr.ib(default=False)
    links: Optional[UserLinks] = attr.ib(default=None)


@attr.s
class MetadataFile(object):
    characters: Dict[str, Character] = attr.ib()
    species_softname: Optional[Dict[str, str]] = attr.ib(default=None)
    tag_aliases: Optional[Dict[str, str]] = attr.ib(default=None)
    tag_descriptions: Optional[Dict[str, str]] = attr.ib(default=None)
    tag_softname: Optional[Dict[str, str]] = attr.ib(default=None)
