import re
import os
import glob
import itertools
import yaml


clean_string_regex = re.compile("[^a-zA-Z0-9]")


def clean_string(value):
    return clean_string_regex.sub('', value)


def validate_file(infile, item):
    '''Validate an artist yaml file'''
    errors = []
    filedir = os.path.dirname(infile)
    artistdir = os.path.basename(filedir)

    def log(msg):
        errors.append("%s: %s" % (artistdir, msg))

    if "artist" not in item:
        log("Missing artist section")

    artist = item["artist"]
    if not isinstance(artist, dict):
        log("Artist section is not a dictionary")
    else:
        if "name" not in artist:
            log("Artist section is missing name")

    if "files" not in item:
        log("Missing files section")

    files = item["files"]
    if not isinstance(files, list):
        log("Files section is not an array")
    else:
        for f in files:
            if "filename" not in f:
                log("A file is missing a filename")

            filename = f["filename"]
            relpath = "%s/%s" % (filedir, filename)
            f["relpath"] = relpath  # TODO: Move this somewhere else!

            if not os.path.exists(relpath):
                log("File %s is missing" % (filename))

            if "date" not in f:
                log("File %s is missing a date" % (filename))

            if "slug" not in f:
                log("File %s is missing a slug" % (filename))

            if "title" not in f:
                log("File %s is missing a title" % (filename))

            if "tags" not in f:
                log("File %s is missing tags" % (filename))
            elif not isinstance(f["tags"], list):
                log("File %s tags are not an array" % (filename))

            if "characters" not in f:
                log("File %s is missing characters" % (filename))
            elif not isinstance(f["characters"], str) and not isinstance(f["characters"], list):
                log("File %s characters are in an invalid format" % (filename))

    return errors


def load_file(filename):
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj["files"] = list(map(lambda x: update_extra(filename, x), obj["files"]))
        errors = validate_file(filename, obj)
        return (obj, errors)


def update_extra(filename, item):
    filedir = os.path.dirname(filename)
    relpath = "%s/%s" % (filedir, item["filename"])
    item["relpath"] = relpath
    return item


def process_lockout(item, limit="*"):
    '''Handle limit'''
    is_visible = True

    if limit == "*":
        # Everything
        is_visible = True
    elif limit is None:
        # Everything not locked out
        is_visible = "lockout" not in item
    else:
        # Only lockouts
        is_visible = "lockout" in item and item["lockout"] == limit

    return item if is_visible else None


def get_artist_files(path):
    return glob.glob(path + "/**/.art.yaml")


def flatten(iterable):
    return [item for sublist in iterable for item in sublist]


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


def get_art_data(path, limit):
    '''Get some art data.'''
    artist_files = get_artist_files(path)
    artist_list = map(load_file, artist_files)
    (artist_list, errors) = zip(*list(artist_list))

    # Handle the limit/lockout
    for i in artist_list:
        i["files"] = list(filter(None, map(lambda x: process_lockout(x, limit), i["files"])))

    # Artists
    artist_map = {}

    def artist_handler(item):
        artist = item["artist"]
        name = artist["name"]
        artist["slug"] = clean_string(name.lower())
        artist_map[name] = artist
        artist["images"] = item["files"]

        return artist if len(artist["images"]) > 0 else None

    artists = list(filter(None, map(artist_handler, artist_list)))

    # Files
    def file_handler(item):
        artist = item["artist"]

        def inner_handler(f):
            f["artist"] = artist_map[artist["name"]]
            f["outputfile"] = "%s_%s" % (artist["slug"], f["slug"])  # TODO: Different hash
            img_fn, img_ext = os.path.splitext(f["filename"])
            f["imgext"] = img_ext[1:]
            return f

        return map(inner_handler, item["files"])

    files = list(filter(None, flatmap(file_handler, artist_list)))

    # Tags, species and characters
    tag_list = {}
    species_list = {}
    character_list = {}

    def add_dict(dic, key, value):
        if key not in dic:
            dic[key] = []
        dic[key].append(value)

    for f in files:
        for t in f["tags"]:
            if t.startswith("species#"):
                species_name = t[8:]
                add_dict(species_list, species_name, f)
            else:
                add_dict(tag_list, t, f)

        chars = f["characters"]
        if isinstance(chars, str):
            add_dict(character_list, chars, f)
        elif isinstance(chars, list):
            for c in chars:
                add_dict(character_list, c, f)
        else:
            raise Exception("Unable to process non-string or list characters")

        # TODO: Pull in the character data file and tie species

    for c, f in character_list.items():
        if "#" in c:
            species = c.split("#")[1]  # Ignore anything after for this use case
            add_dict(species_list, species, f)

    # TODO: Check for duplicate artists or files

    output = {
        "artists": artists, "files": files, "tags": tag_list,
        "species": species_list, "characters": character_list
    }
    errors = list(flatten(filter(None, errors)))

    return (output, errors)
