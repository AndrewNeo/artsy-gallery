import re
import os
import attr
from attr.validators import instance_of, optional
import cattr
from cattr.vendor.typing import List, Dict, Optional


clean_string_regex = re.compile("[^a-zA-Z0-9]")


def clean_string(value):
    return clean_string_regex.sub('', value)


@attr.s
class UserLinks(object):
    fa = cattr.typed(Optional[str], default=None)
    weasyl = cattr.typed(Optional[str], default=None)


@attr.s
class ImageLinks(object):
    fa = cattr.typed(Optional[int], default=None)
    weasyl = cattr.typed(Optional[str], default=None)

    def get_fa(self):
        return "https://www.furaffinity.net/view/{}/".format(self.fa) if self.fa else None


@attr.s
class Artist(object):
    name = cattr.typed(str)
    links = cattr.typed(Optional[UserLinks], default=None)

    artist_file = None  # Link to parent ArtistFile

    def get_slug(self):
        return clean_string(self.name.lower())

    def get_files(self, limit=None):
        return filter(lambda x: x.is_visible(limit), self.artist_file.files)


def make_list(x):
    if isinstance(x, list):
        return x
    return [x]


@attr.s
class ArtistImage(object):
    filename = cattr.typed(str)
    title = cattr.typed(str)
    slug = cattr.typed(str, convert=clean_string)
    date = cattr.typed(int)
    description = cattr.typed(Optional[str])
    tags = cattr.typed(List[str])
    characters = attr.ib(convert=make_list)  # Using cattr.typed converts str to a list before convert is called
    lockout = cattr.typed(Optional[str], default=None)
    my_links = cattr.typed(Optional[ImageLinks], default=None)
    artist_links = cattr.typed(Optional[ImageLinks], default=None)

    artist_file = None  # Link to parent ArtistFile
    artist = None  # Link to parent Artist
    character_list = []  # List of Character attached to this
    tag_list = []  # List of Tag attached to this
    thumbnails = {}  # Generated thumbnails

    def get_file_ext(self):
        img_fn, img_ext = os.path.splitext(self.filename)
        return img_ext[1:]

    def get_relative_path(self):
        return os.path.join(self.artist_file.path, self.filename)

    def is_visible(self, limit):
        if limit == "*":
            # Everything
            return True
        elif limit is None:
            # Everything not locked out
            return self.lockout is None
        else:
            # Only lockouts
            return self.lockout == limit


@attr.s
class ArtistFile(object):
    artist = cattr.typed(Artist)
    files = cattr.typed(List[ArtistImage])
    path = None

    def prepare(self, filename):
        '''Process parent-links and add metadata.'''
        self.path = os.path.dirname(filename)
        self.artist.artist_file = self

        for f in self.files:
            f.artist_file = self
            f.artist = self.artist


@attr.s
class CharacterSpeciesSubform(object):
    refsheet = cattr.typed(Optional[Dict[str, str]], default=None)
    description = cattr.typed(Optional[str], default=None)
    localid = None
    character = None
    species = None
    files = []

    def is_subform(self):
        return True

    def get_files(self, limit=None):
        return filter(lambda x: x.is_visible(limit), self.files)


@attr.s
class CharacterSpecies(CharacterSpeciesSubform):
    subforms = cattr.typed(Optional[Dict[str, Optional[CharacterSpeciesSubform]]], default=None)

    def is_subform(self):
        return False

    def get_files(self, limit=None):
        yield from filter(lambda x: x.is_visible(limit), self.files)
        if self.subforms:
            for sfn, sf in self.subforms.items():
                yield from sf.get_files(limit)


@attr.s
class Character(object):
    name = cattr.typed(str)
    species = cattr.typed(Dict[str, Optional[CharacterSpecies]])
    description = cattr.typed(Optional[str], default=None)
    owner = cattr.typed(Optional[str], default=None)
    root = cattr.typed(Optional[bool], default=False)
    links = cattr.typed(Optional[UserLinks], default=None)

    def get_files(self, limit=None):
        for sn, s in self.species.items():
            yield from s.get_files(limit)


@attr.s
class CharacterFile(object):
    species = cattr.typed(Dict[str, str])
    characters = cattr.typed(Dict[str, Character])

    def prepare(self):
        '''Process parent-links and add metadata.'''
        for cn, c in self.characters.items():
            for sn, s in c.species.items():
                if s is None:
                    s = CharacterSpecies()
                    c.species[sn] = s

                s.localid = sn
                s.character = c
                if s.subforms:
                    for sfn, sf in s.subforms.items():
                        if sf is None:
                            sf = CharacterSpeciesSubform()
                            s.subforms[sfn] = sf

                        sf.localid = "{0}#{1}".format(sn, sfn)
                        sf.character = c
                        sf.species = s

    def find_character(self, raw):
        split = raw.split("#")
        name = split[0]
        species = split[1]
        subform = None
        if len(split) > 2:
            subform = split[2]

        for n, c in self.characters.items():
            if n == name:
                for spn, sp in c.species.items():
                    if spn == species:
                        if subform:
                            for sfn, sf in sp.subforms.items():
                                if sfn == subform:
                                    return sf
                            return None
                        else:
                            return sp
                return None
        return None
