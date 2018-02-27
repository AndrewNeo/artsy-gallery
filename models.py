import re
import os
import functools
import itertools
import attr
import cattr
from typing import List, Dict, Optional


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
        sval = kwargs["sort"] if "sort" in kwargs else None
        return sort_files(output, sval)
    return wrapper


def autovisfilter(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        if "limit" in kwargs:
            lval = kwargs["limit"]
            if lval:
                return filter(lval.is_visible, output)
            else:
                return output
        else:
            return output
    return wrapper


def flatmap(func, iterable):
    return itertools.chain.from_iterable(map(func, iterable))


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
class ImageSequence(object):
    first = cattr.typed(Optional[str], default=None)
    next = cattr.typed(Optional[str], default=None)


@attr.s
class Artist(object):
    name = cattr.typed(str)
    links = cattr.typed(Optional[UserLinks], default=None)

    def get_slug(self):
        return clean_string(self.name.lower())


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
    visibility = cattr.typed(Optional[str], default=None)
    lockout = cattr.typed(Optional[str], default=None)
    sequence = cattr.typed(Optional[ImageSequence], default=None)
    my_links = cattr.typed(Optional[ImageLinks], default=None)
    artist_links = cattr.typed(Optional[ImageLinks], default=None)

    def get_artist(self):
        return self._artist

    def set_artist(self, artist):
        self._artist = artist

    def get_file_ext(self):
        img_fn, img_ext = os.path.splitext(self.filename)
        return img_ext[1:]

    def get_thumbnail_name(self, size):
        return "{slug}_{size}.{ext}".format(size=size, slug=self.slug, ext=self.get_file_ext())

    def is_visible(self, limit=None):
        return limit.is_visible(self)

    def get_species_all(self):
        yield from map(lambda c: Core.split_character_name(c)[1], self.characters)
        yield from map(Core.split_species, filter(lambda t: t.startswith("species#"), self.tags))

    def get_species(self):
        return set(self.get_species_all())

    def get_groups(self):
        return set(map(lambda t: t.replace("group#", ""), filter(lambda t: t.startswith("group#"), self.tags)))


@attr.s
class ArtistFile(object):
    artist = cattr.typed(Artist)
    files = cattr.typed(List[ArtistImage])

    def prepare(self, filename):
        self._reldir = os.path.dirname(filename)
        for f in self.files:
            f.set_artist(self.artist)

    def get_dir(self):
        return self._reldir

    @autosort
    @autovisfilter
    def get_files(self, sort=None, limit=None):
        return self.files


@attr.s
class CharacterSpeciesSubform(object):
    refsheet = cattr.typed(Optional[Dict[str, str]], default=None)
    description = cattr.typed(Optional[str], default=None)

    def set_character(self, character):
        self._character = character

    def get_character(self):
        return self._character

    def set_parent(self, parent):
        self._parent = parent

    def get_parent(self):
        return self._parent

    def is_subform(self):
        return True


@attr.s
class CharacterSpecies(CharacterSpeciesSubform):
    subforms = cattr.typed(Optional[Dict[str, Optional[CharacterSpeciesSubform]]], default=None)

    def is_subform(self):
        return False


@attr.s
class Character(object):
    name = cattr.typed(str)
    species = cattr.typed(Dict[str, Optional[CharacterSpecies]])
    description = cattr.typed(Optional[str], default=None)
    owner = cattr.typed(Optional[str], default=None)
    root = cattr.typed(Optional[bool], default=False)
    links = cattr.typed(Optional[UserLinks], default=None)


@attr.s
class MetadataFile(object):
    tags = cattr.typed(Dict[str, str])
    species = cattr.typed(Dict[str, str])
    characters = cattr.typed(Dict[str, Character])

    def prepare(self):
        for cn, c in self.characters.items():
            for sn, s in c.species.items():
                if not s:
                    s = CharacterSpecies()
                    c.species[sn] = s

                s.set_character(c)
                s.set_parent(c)

                if s.subforms:
                    for sfn, sf in s.subforms.items():
                        sf.set_character(c)
                        sf.set_parent(s)


@attr.s
class Core(object):
    artist_files = attr.ib(convert=list)

    tag_key = attr.ib()
    species_key = attr.ib()
    character_list = attr.ib()

    def get_all_artists(self):
        return self.artist_files

    def get_artist_by_name(self, artist_name, use_slug=False):
        def artist_filter(a):
            if use_slug:
                return a.artist.get_slug() == artist_name
            else:
                return a.artist.name == artist_name

        return next(filter(artist_filter, self.artist_files), None)

    @autosort
    @autovisfilter
    def get_files_by_artist(self, artist_name, use_slug=False, sort=None, limit=None):
        artist = self.get_artist_by_name(artist_name, use_slug)
        if not artist:
            return []

        return artist.files

    @autosort
    @autovisfilter
    def get_all_files(self, sort=None, limit=None):
        return flatmap(lambda a: a.files, self.artist_files)

    def get_file_by_slug(self, artist, slug):
        return next(filter(lambda f: f.slug == slug, self.get_files_by_artist(artist, use_slug=True)), None)

    def get_all_tags(self, limit=None, ignore=None):
        tags = flatmap(lambda f: f.tags, self.get_all_files(limit=limit))

        if ignore:
            if isinstance(ignore, str):
                ignore = [ignore]

            tags = itertools.filterfalse(lambda tag: any(map(lambda x: tag.startswith("{}#".format(x)), ignore)), tags)

        return set(tags)

    @autosort
    def get_files_by_tag(self, tag_name, sort=None, limit=None):
        return filter(lambda f: tag_name in f.tags, self.get_all_files(limit=limit))

    def get_tag_details(self, tag_name, as_none=False):
        if tag_name in self.tag_key:
            return self.tag_key[tag_name]
        elif as_none:
            return None
        else:
            return tag_name

    @staticmethod
    def split_species(raw):
        split = raw.split("#")
        return split[1]

    def get_all_species(self, limit=None):
        def get_species_from_file(f):
            yield from map(Core.split_species, f.characters)
            yield from map(Core.split_species, filter(lambda f: f.startswith("species#"), f.tags))

        return set(flatmap(get_species_from_file, self.get_all_files(limit=limit)))

    @autosort
    def get_files_by_species(self, species_name, sort=None, limit=None):
        all_files = list(self.get_all_files(limit=limit))

        yield from filter(lambda f: any(map(lambda c: Core.split_species(c) == species_name, f.characters)), all_files)
        yield from filter(lambda f: "species#{}".format(species_name) in f.tags, all_files)

    def get_species_details(self, species_name, as_none=False):
        if species_name in self.species_key:
            return self.species_key[species_name]
        elif as_none:
            return None
        else:
            return species_name

    def get_all_characters(self, limit=None):
        return set(flatmap(lambda f: f.characters, self.get_all_files(limit=limit)))

    @staticmethod
    def split_character_name(character_name):
        split = character_name.split("#")
        name = split[0]
        species = split[1] if len(split) > 1 else None
        subform = split[2] if len(split) > 2 else None

        return (name, species, subform)

    @autosort
    def get_files_by_character(self, character_name, species=None, subform=None, ignore_subforms=False, sort=None, limit=None):
        def charfilter(f):
            for char in f.characters:
                if character_name == char:
                    return True

                (iname, ispec, isub) = Core.split_character_name(char)
                if character_name == iname:
                    if isub and ignore_subforms:
                        return False

                    if (not species or species == ispec) and (not subform or subform == isub):
                        return True

            return False

        return filter(charfilter, self.get_all_files(limit=limit))

    def get_character_details(self, character_name):
        (name, species, subform) = Core.split_character_name(character_name)

        def notfound():
            raise ValueError("Could not find character {}".format(character_name))

        for n, c in self.character_list.items():
            if n == name:
                if not species:
                    return c

                for spn, sp in c.species.items():
                    if spn == species:
                        if not subform:
                            return sp

                        for sfn, sf in sp.subforms.items():
                            if sfn == subform:
                                return sf

                        return notfound()

                return notfound()

        return notfound()

    def get_character_breakdown(self, character_name):
        (name, species, subform) = Core.split_character_name(character_name)
        character = self.get_character_details(character_name)

        return {
            "name": name,
            "species_name": species,
            "subform_name": subform,
            "character": character
        }

    def lookup_ref(self, path):
        refdir, filename = path.split("/", 2)
        return next(filter(lambda f: f.filename == filename, self.get_files_by_artist(refdir)), None)

    @autovisfilter
    def get_refsheets_from_character_species(self, species, limit=None):
        if not species.refsheet:
            return None

        return {version: self.lookup_ref(path) for version, path in species.refsheet}

    def get_refsheet_from_character_species(self, species, version="sfw", limit=None):
        sheets = self.get_refsheets_from_character_species(species, limit=limit)
        if version not in sheets:
            return None

        return sheets[version]

    def process_sequence(self, file):
        def get_file_from_seqdef(str):
            (artist, slug) = str.split(":")
            return self.get_file_by_slug(artist, slug)

        # Get first file
        if not file.sequence:
            return []

        if file.sequence.next and not file.sequence.first:
            # This is the first file
            curfile = file
        elif file.sequence.first:
            curfile = get_file_from_seqdef(file.sequence.first)
            if not curfile:
                raise RuntimeError("File {} in sequence was unable to find slug {}".format(file.filename, file.sequence.first))
        else:
            # Empty sequence
            return []

        sequence = [curfile]

        # Chain next's
        while curfile and curfile.sequence and curfile.sequence.next:
            curfile = get_file_from_seqdef(curfile.sequence.next)
            if curfile:
                if curfile in sequence:
                    raise RecursionError("File {} was already in sequence".format(file.filename))

                sequence.append(curfile)
            else:
                raise RuntimeError("File {} in sequence was unable to find slug {}".format(file.filename, file.sequence.next))

        if file not in sequence:
            raise RuntimeError("Current file {} is not in sequence".format(file.filename))

        if len(sequence) < 2:
            raise RuntimeError("Current file {} is the only member in the sequence".format(file.filename))

        return sequence

    def get_sequence(self, file):
        seqlist = self.process_sequence(file)
        if len(seqlist) < 2:
            return None

        p = seqlist.index(file)

        return {
            "list": seqlist,
            "curpos": p,
            "first": seqlist[0],
            "last": seqlist[-1],
            "prev": seqlist[p - 1] if p > 0 else None,
            "next": seqlist[p + 1] if p < len(seqlist) - 1 else None
        }
