import re
import os
import functools
import attr
import cattr
from cattr.vendor.typing import List, Dict, Optional


clean_string_regex = re.compile("[^a-zA-Z0-9]")


def clean_string(value):
    return clean_string_regex.sub('', value)


def sort_by_name(f):
    return f.title


def sort_by_date(f):
    return f.date


def sort_files(files, sort=None):
    key = None
    reverse = False

    if sort == "name":
        key = sort_by_name
    elif sort == "rdate":
        key = sort_by_date
    else:
        # Date by default
        key = sort_by_date
        reverse = True

    return sorted(files, key=key, reverse=reverse)


def autosort(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        if "sort" in kwargs:
            sval = kwargs["sort"]
            return sort_files(output, sval)
        else:
            return sort_files(output)
    return wrapper


def vis_filter(files, limit):
    return filter(lambda x: x.is_visible(limit), files)


def autovisfilter(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        if "limit" in kwargs:
            lval = kwargs["limit"]
            return vis_filter(output, lval)
        else:
            return output
    return wrapper


def create_extra_attr(default=None, repr=False):
    return attr.ib(init=False, repr=repr, cmp=False, default=default)


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


# Classes

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

    # Extra attributes
    artist_file = create_extra_attr()  # Link to parent ArtistFile

    def get_slug(self):
        return clean_string(self.name.lower())

    @autosort
    @autovisfilter
    def get_files(self, sort=None, limit=None):
        return self.artist_file.files


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

    # Extra attributes
    artist_file = create_extra_attr()  # Link to parent ArtistFile
    artist = create_extra_attr(repr=True)  # Link to parent Artist
    character_list = create_extra_attr(default=attr.Factory(list))  # List of Character attached to this
    tag_list = create_extra_attr(default=attr.Factory(list))  # List of Tag attached to this
    species_list = create_extra_attr(default=attr.Factory(list))  # List of Species attached to this
    thumbnails = create_extra_attr(default=attr.Factory(dict))  # Generated thumbnails

    def get_file_ext(self):
        img_fn, img_ext = os.path.splitext(self.filename)
        return img_ext[1:]

    def get_relative_path(self):
        return os.path.join(self.artist_file.path, self.filename)

    def is_visible(self, limit=None):
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

    # Extra attributes
    path = create_extra_attr()

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

    # Extra attributes
    localid = create_extra_attr()
    character = create_extra_attr()
    species = create_extra_attr()
    files = create_extra_attr(default=attr.Factory(list))

    def is_subform(self):
        return True

    @autosort
    @autovisfilter
    def get_files(self, sort=None, limit=None):
        return self.files


@attr.s
class CharacterSpecies(CharacterSpeciesSubform):
    subforms = cattr.typed(Optional[Dict[str, Optional[CharacterSpeciesSubform]]], default=None)

    def is_subform(self):
        return False

    @autosort
    def get_files(self, sort=None, limit=None):
        yield from vis_filter(self.files, limit)
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

    @autosort
    def get_files(self, sort=None, limit=None):
        for sn, s in self.species.items():
            yield from s.get_files(limit)


@attr.s
class MetadataFile(object):
    tags = cattr.typed(Dict[str, str])
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

    def prepare_files(self, files):
        for f in files:
            for cn in f.characters:
                char = self.find_character(cn)
                if not char:
                    continue

                char.files.append(f)
                char.files.append(f.filename + " to " + char.localid)

                if char not in f.character_list:
                    f.character_list.append(char)

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


@attr.s
class Tag(object):
    full_tag = attr.ib()
    name = attr.ib()
    tail = attr.ib(default=None)
    description = attr.ib(default=None)
    files = create_extra_attr(default=attr.Factory(list))

    @autosort
    @autovisfilter
    def get_files(self, sort=None, limit=None):
        return self.files


@attr.s
class TagContainer(object):
    descriptions = attr.ib(repr=False, default=attr.Factory(dict))
    tags = create_extra_attr(default=attr.Factory(list))

    def get_or_create(self, fullname):
        if fullname in self.tags:
            return self.tags[fullname]

        split = fullname.split("#")
        name = fullname
        tail = None
        if len(split) > 0:
            name = split[0]
        if len(split) > 1:
            tail = split[1]

        desc = self.descriptions[fullname] if fullname in self.descriptions else None

        nt = Tag(fullname, name, tail, desc)
        self.tags[fullname] = nt
        return nt

    def prepare(self, files):
        for f in files:
            for t in f.tags:
                nt = self.get_or_create(t)

                if f not in nt.files:
                    nt.files.append(f)

                if nt not in f.tag_list:
                    f.tag_list.append(nt)
            
    def items(self):
        return self.tags.items()

    def get_by_name(self, name):
        return filter(lambda x: x.name == name, self.tags.values())

    def get_files(self, name, sort=None, limit=None):
        return self.tags[name].get_files(sort=sort, limit=limit)


@attr.s
class Species(object):
    slug = attr.ib()
    description = attr.ib(default=None)
    files = create_extra_attr(default=attr.Factory(list))

    @autosort
    @autovisfilter
    def get_files(self, sort=None, limit=None):
        return self.files


@attr.s
class SpeciesContainer(object):
    descriptions = attr.ib(repr=False)
    species = create_extra_attr(default=attr.Factory(dict))

    def get_or_create(self, species_name):
        if species_name in self.species:
            return self.species[species_name]

        desc = self.descriptions[species_name] if species_name in self.descriptions else None

        ns = Species(species_name, desc)
        self.species[species_name] = ns
        return ns

    def prepare_single(self, species_name, files):
        if not species_name:
            return

        for f in files:
            ns = self.get_or_create(species_name)

            if f not in ns.files:
                ns.files.append(f)

            if ns not in f.species_list:
                f.species_list.append(ns)

    def prepare(self, tag_container, characters):
        # Handle species from tags
        for t in tag_container.get_by_name("species"):
            self.prepare_single(t.tail, t.files)

        # Handle species from characters
        for cn, c in characters.items():
            for sn, s in c.species.items():
                self.prepare_single(sn, s.files)

    def items(self):
        return self.species.items()

    def get_files(self, name, sort=None, limit=None):
        return self.species[name].get_files(sort=sort, limit=limit)
