import os
import glob
import yaml
import cattr
from models import Core, ArtistFile, MetadataFile


def load_artist_file(filename):
    '''Load an artist file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, ArtistFile)
        obj.prepare(filename)
        return obj


def get_artist_files(path):
    return glob.iglob(os.path.join(path, "**", ".art.yaml"))


def load_metadata_file(filename):
    '''Load a metadata file.'''
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj = cattr.structure(obj, MetadataFile)
        obj.prepare()
        return obj


def get_art_data(path, limit):
    '''Get some art data.'''
    # Artist directory files
    artist_files = map(load_artist_file, get_artist_files(path))

    # Character list
    metadata = load_metadata_file(os.path.join(path, ".metadata.yaml"))

    species_key = metadata.species
    character_list = metadata.characters
    tag_key = metadata.tags

    output = Core(artist_files, tag_key, species_key, character_list)
    return output
