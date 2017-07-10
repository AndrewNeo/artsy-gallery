#!/usr/bin/env python3
'''Artsy, an artsy sort of gallery.'''

import os
import shutil
from distutils.dir_util import copy_tree
from resizeimage import resizeimage
from PIL import Image
from data import get_art_data
from templater import Templater


templater = Templater("templates")


def generate_thumbnail_size(img, width, filename):
    thumb = resizeimage.resize_thumbnail(img, [width, width])
    thumb.save(filename, img.format)


def generate_thumbnails(artistdir, image, widths):
    thumbnails = {}
    relpath = image.get_relative_path()

    def get_path(size):
        return os.path.join(artistdir, "{slug}_{size}.{imgext}".format(size=size, slug=image.slug, imgext=image.get_file_ext()))

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

    # Generate image templates
    for image in data["files"]:
        artistdir = os.path.join(output_dir, image.artist.get_slug())
        if not os.path.exists(artistdir):
            os.makedirs(artistdir)
        outfile = os.path.join(artistdir, "{}.html".format(image.slug))

        # Generate thumbnails
        image.thumbnails = generate_thumbnails(artistdir, image, [120, 512])

        # Write templated file
        with open(outfile, "w") as f:
            td = templater.generate("image", image=image)
            f.write(td)

    # Generate artist templates
    for artist in data["artists"]:
        outfile = os.path.join(output_dir, artist.get_slug(), "index.html")

        # Write templated file
        with open(outfile, "w") as f:
            td = templater.generate("artist", artist=artist, limit=limit)
            f.write(td)

    # Generate index file
    indexfile = os.path.join(output_dir, "index.html")
    with open(indexfile, "w") as f:
        td = templater.generate("index", limit=limit, **data)
        f.write(td)

    return True


if __name__ == "__main__":
    if generate_static_site("testdata", "output"):
        print("Files written.")
    else:
        print("Failed with errors.")
