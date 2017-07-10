import os
import glob
import itertools
import yaml
import cattr
from models import ArtistFile, CharacterFile


def load_artist_file(filename):
    '''Load an artist file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, ArtistFile)
        obj.prepare(filename)
        return obj


def get_artist_files(path):
    return glob.glob(os.path.join(path, "**", ".art.yaml"))


def load_character_file(filename):
    '''Load a character file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, CharacterFile)
        obj.prepare()
        return obj


def flatten(iterable):
    return [item for sublist in iterable for item in sublist]


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


def get_art_data(path, limit):
    '''Get some art data.'''
    # Artist directory files
    artist_files = get_artist_files(path)
    art_data = list(map(load_artist_file, artist_files))

    # Artists
    artists = list(map(lambda x: x.artist, art_data))

    # Image files
    files = list(filter(lambda x: x.is_visible(limit), flatmap(lambda x: x.files, art_data)))

    # Character list
    character_data = load_character_file(os.path.join(path, ".characters.yaml"))
    species_key = character_data.species
    character_list = character_data.characters

    character_key = {}
    for c, v in character_list.items():
        character_key[c] = v.name

    # Tags, species and characters
    tag_list = {}
    species_list = {}

    def add_dict(dic, key, value):
        if key not in dic:
            dic[key] = []
        dic[key].append(value)

    for f in files:
        f.character_list = list(map(character_data.find_character, f.characters))

        # Add file to character
        for c in f.character_list:
            c.files.append(f)
            if not c.is_subform():
                add_dict(species_list, c.localid, f)

        # Handle file tags
        for t in f.tags:
            meta_val = None
            if "#" in t:
                tag_name, meta_val = t.split("#", 2)
            else:
                tag_name = t

            # Add file to species list
            if tag_name == "species":
                add_dict(species_list, meta_val, f)

            add_dict(tag_list, t, f)

    # Function output
    output = {
        "artists": artists, "files": files, "tags": tag_list,
        "species": species_list, "species_key": species_key,
        "characters": character_list, "character_key": character_key
    }

    return output
