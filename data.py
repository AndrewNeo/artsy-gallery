import re
import os
import glob
import itertools
import yaml


clean_string_regex = re.compile("[^a-zA-Z0-9]")


def clean_string(value):
    return clean_string_regex.sub('', value)


def validate_artist_file(infile, item):
    '''Validate an artist yaml file'''
    errors = []
    filedir = os.path.dirname(infile)
    artistdir = os.path.basename(filedir)

    def log(msg):
        errors.append("{0}: {1}".format(artistdir, msg))

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
            relpath = os.path.join(filedir, filename)
            f["relpath"] = relpath  # TODO: Move this somewhere else!

            def sublog(msg):
                log("File {0} {1}".format(filename, msg))

            if not os.path.exists(relpath):
                sublog("is missing")

            if "date" not in f:
                sublog("is missing a date")

            if "slug" not in f:
                sublog("is missing a slug")

            if "title" not in f:
                sublog("is missing a title")

            if "tags" not in f:
                sublog("is missing tags")
            elif not isinstance(f["tags"], list):
                sublog("tags are not an array")

            if "characters" not in f:
                log("is missing characters")
            elif not isinstance(f["characters"], str) and not isinstance(f["characters"], list):
                log("characters are in an invalid format")

    return errors


def load_artist_file(filename):
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        obj["files"] = list(map(lambda x: update_extra(filename, x), obj["files"]))
        errors = validate_artist_file(filename, obj)
        return (obj, errors)


def update_extra(filename, item):
    filedir = os.path.dirname(filename)
    relpath = os.path.join(filedir, item["filename"])
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
    return glob.glob(os.path.join(path, "**", ".art.yaml"))


def validate_characters_file(infile, item):
    errors = []

    def log(msg):
        errors.append("Characters file: {}".format(msg))

    if not isinstance(item, dict):
        log("is not dict")

    if "species" not in item:
        log("Missing species section")
    else:
        species = item["species"]

    if "characters" not in item:
        log("Missing characters section")
    else:
        characters = item["characters"]

        for char_name, v in characters.items():
            def sublog(msg):
                log("Character {0} {1}".format(char_name, msg))

            if not isinstance(v, dict):
                sublog("is not dict")
            
            if "name" not in v:
                sublog("is missing name")

            if "owner" not in v:
                sublog("is missing owner")

            if "links" in v and not isinstance(v["links"], dict):
                sublog("links are not dict")

            if "species" not in v:
                sublog("is missing species")

            # Validate species node
            for species, s in v["species"].items():
                if s is None:
                    # Allowed to be empty
                    continue

                def sublog2(msg):
                    sublog("species {0} {1}".format(species, msg))

                if "refsheet" in s and not isinstance(s["refsheet"], dict):
                    sublog2("refsheets are not dict")
                
                if "subforms" in s and not isinstance(s["subforms"], dict):
                    sublog2("subforms are not dict")

    return errors


def load_character_file(filename):
    with open(filename, "r") as f:
        obj = yaml.load(f.read())
        errors = validate_characters_file(filename, obj)
        return (obj, errors)


def flatten(iterable):
    return [item for sublist in iterable for item in sublist]


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


def get_art_data(path, limit):
    '''Get some art data.'''
    # Artist directory files
    artist_files = get_artist_files(path)
    artist_list = map(load_artist_file, artist_files)
    (artist_list, artist_errors) = zip(*list(artist_list))
    artist_errors = list(flatten(filter(None, artist_errors)))

    # Character list
    (character_list, character_errors) = load_character_file(os.path.join(path, ".characters.yaml"))
    species_key = character_list["species"]
    character_list = character_list["characters"]

    character_key = {}
    for c, v in character_list.items():
        character_key[c] = v["name"]

    # Handle errors
    errors = artist_errors + character_errors
    if len(errors) > 0:
        return (None, errors)

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
    used_specs = []

    def get_char(f, cn):
        split = cn.split("#")
        subform_str = None

        def log(msg):
            errors.append("File {0} {1}".format(f["filename"], msg))

        if len(split) == 1:
            log("missing split tag for character {}".format(cn))
            return None
        if len(split) > 1:
            name = split[0]
            species_str = split[1]
        if len(split) > 2:
            subform_str = split[2]

        if name not in character_list:
            log("using undefined character {0}".format(name))
            return None

        character = character_list[name]

        if species_str not in character["species"]:
            log("using undefined species {1} for {0}".format(name, species_str))
            return None

        if character["species"][species_str] is None:
            character["species"][species_str] = {}
        species = character["species"][species_str]

        subform = None
        used_specs.append(species)

        if subform_str:
            if "subforms" not in species:
                log("missing subforms section for {0} {1}".format(name, species_str))
                return None

            if subform_str not in species["subforms"]:
                log("using undefined subform {2} for {0} {1}".format(name, species_str, subform_str))
                return None

            subform = species["subforms"][subform_str]
            if "images" not in subform:
                subform["images"] = []
            subform["images"].append(f)

            used_specs.append(species)
        else:
            if "images" not in species:
                species["images"] = []
            species["images"].append(f)

        return {
            "character": character,
            "species": species,
            "subform": subform,
            "character_id": name,
            "species_id": species_str,
            "subform_id": subform_str,
            "has_subform": subform is not None
        }

    def file_handler(item):
        artist = item["artist"]

        def inner_handler(f):
            f["artist"] = artist_map[artist["name"]]
            characters = f["characters"]
            if not isinstance(characters, list):
                characters = [characters]

            f["characters"] = list(map(lambda x: get_char(f, x), characters))
            f["outputfile"] = "{0}_{1}".format(artist["slug"], f["slug"])  # TODO: Different hash
            img_fn, img_ext = os.path.splitext(f["filename"])
            f["imgext"] = img_ext[1:]
            return f

        return map(inner_handler, item["files"])

    files = list(filter(None, flatmap(file_handler, artist_list)))

    # Check for errors again
    if len(errors) > 0:
        return (None, errors)

    # TODO: Remap refsheet files to character species

    # Tags, species and characters
    tag_list = {}
    species_list = {}

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
                if "#" in t:
                    st = t.split("#", 1)[0]
                    add_dict(tag_list, st, f)
                add_dict(tag_list, t, f)

        # Add image to character
        for c in f["characters"]:
            if c["subform"]:
                c["subform"]["images"].append(f)
            else:
                c["species"]["images"].append(f)
            
            add_dict(species_list, c["species_id"], f)

    # TODO: Remove characters with no attached images

    # Function output
    output = {
        "artists": artists, "files": files, "tags": tag_list,
        "species": species_list, "species_key": species_key,
        "characters": character_list, "character_key": character_key
    }
    return (output, errors)
