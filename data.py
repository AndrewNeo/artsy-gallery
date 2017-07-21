import os
import glob
import itertools
import yaml
import cattr
from models import ArtistFile, MetadataFile, TagContainer, SpeciesContainer, sort_files


def load_artist_file(filename):
    '''Load an artist file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, ArtistFile)
        obj.prepare(filename)
        return obj


def get_artist_files(path):
    return glob.glob(os.path.join(path, "**", ".art.yaml"))


def load_metadata_file(filename):
    '''Load a metadata file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, MetadataFile)
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
    files = list(sort_files(filter(lambda x: x.is_visible(limit), flatmap(lambda x: x.files, art_data)), "name"))

    # Character list
    metadata = load_metadata_file(os.path.join(path, ".metadata.yaml"))
    metadata.prepare_files(files)

    species_key = metadata.species
    character_list = metadata.characters
    tag_key = metadata.tags

    # Tags, species and characters
    tag_list = {}
    species_list = {}

    tag_list = TagContainer(tag_key)
    tag_list.prepare(files)

    species_list = SpeciesContainer(species_key)
    species_list.prepare(tag_list, character_list)

    # Function output
    output = {
        "artists": artists,
        "files": files,
        "tags": tag_list,
        "species": species_list,
        "characters": character_list
    }

    return output
