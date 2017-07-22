#!/usr/bin/env python3
'''Artsy, an artsy sort of gallery.'''

import os
import shutil
import json
from distutils.dir_util import copy_tree
from resizeimage import resizeimage
from PIL import Image
import cattr
from data import get_art_data
from templater import Templater


templater = Templater("templates")


def generate_thumbnail_size(img, width, filename):
    thumb = resizeimage.resize_thumbnail(img, [width, width])
    thumb.save(filename, img.format)


def generate_thumbnails(indir, outdir, image, widths):
    thumbnails = {}
    relpath = os.path.join(indir, image.filename)

    def get_path(size):
        return os.path.join(outdir, "{slug}_{size}.{imgext}".format(size=size, slug=image.slug, imgext=image.get_file_ext()))

    # Copy full image file
    fullpath = get_path("full")
    shutil.copy2(relpath, fullpath)
    thumbnails["full"] = os.path.basename(fullpath)

    # Generate actual thumbnails
    with Image.open(relpath) as img:
        for width in list(widths):
            filename = get_path(width)
            generate_thumbnail_size(img, width, filename)
            thumbnails[width] = os.path.basename(filename)

    return thumbnails


def write_page(template, outfile, **kwargs):
    with open(outfile, "w") as f:
        td = templater.generate(template, **kwargs)
        f.write(td)


# https://stackoverflow.com/a/27974027/151495
def clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, clean_empty(v)) for k, v in d.items()) if v}


def write_json(outfile, data):
    destdata = clean_empty(cattr.unstructure(data))
    with open(outfile, "w") as f:
        json.dump(destdata, f)


# TODO: Don't update files that don't need updating
def generate_static_site(input_dir, output_dir, limit="*"):
    '''Output templates to filesystem.'''
    # Get data and fail on error
    data = get_art_data(input_dir, limit)

    # Recreate the output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    # Copy static files (and create output dir)
    copy_tree("static", output_dir)

    # Hold thumbnail paths
    thumbnails = {}

    all_artists = list(data.get_all_artists())
    use_artists = []

    # Generate image and artist templates
    for artist_file in all_artists:
        files = list(artist_file.get_files(limit=limit))
        if len(files) == 0:
            continue

        artist = artist_file.artist
        artistdir = os.path.join(output_dir, artist.get_slug())

        if not os.path.exists(artistdir):
            os.makedirs(artistdir)

        artistout = {
            "artist": artist,
            "files": []
        }

        # Generate image templates
        for image in files:
            outfile = os.path.join(artistdir, "{}.html".format(image.slug))

            # Generate thumbnails
            thumbnails[image.slug] = generate_thumbnails(artist_file._reldir, artistdir, image, [120, 512])

            # Write templated file
            write_page("image", outfile, artist=artist, image=image, thumbnails=thumbnails[image.slug])

            artistout["files"].append(image)

        # Generate artist templates
        artistfile = os.path.join(output_dir, artist.get_slug(), "index.html")

        # Write templated file
        write_page("artist", artistfile, artist=artist, files=files, thumbnails=thumbnails)

        use_artists.append(artistout)

    # Generate all-artists template
    artistsfile = os.path.join(output_dir, "all_artists.html")
    write_page("artists", artistsfile, artists=use_artists, limit=limit, thumbnails=thumbnails)

    # Generate tag templates
    use_tags = list(sorted(data.get_all_tags(limit=limit, ignore="species")))

    tagsdir = os.path.join(output_dir, "_tags")
    if not os.path.exists(tagsdir):
        os.makedirs(tagsdir)

    collected_tags = {}
    for t in use_tags:
        files = data.get_files_by_tag(t, limit=limit)
        collected_tags[t] = files

        outfile = os.path.join(tagsdir, "{}.html".format(t.replace("#", "_")))
        write_page("tag", outfile, tag=t, files=files, thumbnails=thumbnails)

    # Generate all-tags template
    tagfile = os.path.join(output_dir, "all_tags.html")
    write_page("tags", tagfile, tags=collected_tags, thumbnails=thumbnails, get_tag_details=data.get_tag_details)

    # Collect unique characters
    chars = set(map(lambda x: x.split("#")[0], data.get_all_characters(limit=limit)))

    # Generate JSON file
    jsonfile = os.path.join(output_dir, "data.json")
    jsondata = {
        "data": use_artists,
        "tags": use_tags,
        "tag_descriptions": data.tag_key,
        "species": list(sorted(data.get_all_species(limit=limit))),
        "species_descriptions": data.species_key,
        "characters": list(sorted(map(data.get_character_details, chars)))
    }

    write_json(jsonfile, jsondata)

    # Generate index file
    indexfile = os.path.join(output_dir, "index.html")
    indexdata = {
        "limit": limit,
        "thumbnails": thumbnails,
        "files": data.get_all_files(limit=limit),
        "artists": map(lambda x: x["artist"], use_artists),
        "tags": jsondata["tags"],
        "species": jsondata["species"],
        "characters": jsondata["characters"],
        "get_tag_details": data.get_tag_details,
        "get_species_details": data.get_species_details
    }

    write_page("index", indexfile, **indexdata)


if __name__ == "__main__":
    generate_static_site("testdata", "output")
    print("Files written.")
