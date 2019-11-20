#!/usr/bin/env python3
"""Artsy, an artsy sort of gallery."""

import os
import shutil
import glob
from pathlib import Path
from resizeimage import resizeimage
from PIL import Image
from importer import process_art_database
import models_db
import db_helper
from utils import LimitFilter, build_filename
from templater import Templater
import utils


templater = Templater("templates")


def generate_thumbnail_size(img: Image, width: int, filename: str) -> None:
    thumb = resizeimage.resize_thumbnail(img, [width, width])
    thumb.save(filename, img.format)


def generate_thumbnails(
    indir: str,
    outdir: str,
    image: Image,
    widths: [int],
    do_update: bool,
    add_touched: bool,
    force: bool = False,
) -> dict:
    thumbnails = {}
    relpath = os.path.join(indir, image.filename)

    def get_path(size: str):
        return os.path.join(
            outdir,
            "{slug}_{size}.{imgext}".format(
                size=size, slug=image.slug, imgext=image.get_file_ext()
            ),
        )

    # Copy full image file
    fullpath = get_path("full")
    fullhash = utils.get_hash(relpath)
    should_do_update = do_update(fullpath, fullhash)
    if should_do_update:
        shutil.copy2(relpath, fullpath)
    add_touched(fullpath)

    thumbnails["full"] = os.path.basename(fullpath)
    thumbnails["_relpath"] = relpath

    # Generate actual thumbnails
    with Image.open(relpath) as img:
        for width in list(widths):
            filename = get_path(width)
            if should_do_update or not os.path.exists(filename):
                generate_thumbnail_size(img, width, filename)
            thumbnails[width] = os.path.basename(filename)
            add_touched(filename)

    return thumbnails


def write_page(template: str, outfile: str, **kwargs) -> None:
    with open(outfile, "w", encoding="utf-8") as f:
        td = templater.generate(template, **kwargs)
        f.write(td)


def cleanup_dead_files(output_dir: str, tree_hash: dict, touched_files: list) -> None:
    n_tree_hash = set(map(Path, tree_hash.keys()))
    n_touched = set(map(Path, touched_files))
    dead_files = n_tree_hash - n_touched

    for df in dead_files:
        print("Deleting file", df)
        (Path(output_dir) / df).unlink()


def generate_static_site(
    input_dir: str, output_dir: str, base_limit: LimitFilter = None, force: bool = False
) -> None:
    """Output templates to filesystem."""
    # Get data and fail on error
    process_art_database(input_dir)

    touched_files = []
    tree_hash = {}

    def add_touched(filename):
        touched_files.append(utils.remove_parent_path(output_dir, filename))

    def do_update(fullpath, fullhash):
        return (
            force
            or not os.path.exists(fullpath)
            or fullpath not in tree_hash
            or fullhash != tree_hash[fullpath]
        )

    if os.path.exists(output_dir):
        if force:
            # Recreate the output directory
            shutil.rmtree(output_dir, ignore_errors=True)

        # Get all current hashes
        tree_hash = utils.get_dir_hashes(output_dir)
    else:
        # Create output dir
        os.makedirs(output_dir)

    # Copy static files
    static_files = glob.iglob("static/**", recursive=True)
    for filepath in [item for item in static_files if os.path.isfile(item)]:
        filehash = utils.get_hash(filepath)
        newpath = utils.remove_parent_path("static", filepath)
        outfile = os.path.join(output_dir, newpath)
        if do_update(outfile, filehash):
            shutil.copy2(filepath, outfile)
        add_touched(outfile)

    # Hold thumbnail paths
    thumbnails = {}

    # Loop through limits
    # TODO: Missing index.html's for things that don't have root level content
    for limit in db_helper.get_all_limits(base_limit, locked_vis=True):
        submissions = []

        # Hold pathing methods for views
        pathing = {
            "all_artists": models_db.Artist.get_path_all(limit),
            "all_species": models_db.Species.get_path_all(limit),
            "all_tags": models_db.Tag.get_path_all(limit),
            "all_groups": models_db.Group.get_path_all(limit),
            "all_characters": models_db.Character.get_path_all(limit),
        }
        standard_args = {"thumbnails": thumbnails, "pathing": pathing, "limit": limit}

        # Generate image and artist templates
        artists = list(models_db.Artist.get_all(limit=limit))
        for artist in artists:
            artistdir = os.path.join(output_dir, artist.slug())

            if not os.path.exists(artistdir):
                os.makedirs(artistdir)

            # Generate image templates
            for image in artist.submissions_filtered(limit):
                outfile = os.path.join(output_dir, image.get_path(limit=limit))

                # Generate thumbnails
                thumbnails[image.slug] = generate_thumbnails(
                    artist.path, artistdir, image, [120, 512], do_update, add_touched
                )

                # Write templated file
                write_page(
                    "image",
                    outfile,
                    image=image,
                    thumbnails=thumbnails[image.slug],
                    pathing=pathing,
                    limit=limit,
                )
                add_touched(outfile)
                submissions.append(image)

            # Generate artist templates
            artistfile = os.path.join(output_dir, artist.get_path(limit=limit))

            # Write templated file
            write_page("artist", artistfile, artist=artist, **standard_args)
            add_touched(artistfile)

        # Generate all-artists template
        artistsfile = os.path.join(output_dir, models_db.Artist.get_path_all(limit))
        write_page("artists", artistsfile, artists=artists, **standard_args)
        add_touched(artistsfile)

        # Generate tag templates
        tagsdir = os.path.join(output_dir, "_tags")
        if not os.path.exists(tagsdir):
            os.makedirs(tagsdir)

        tags = list(models_db.Tag.get_all(limit=limit))
        for t in tags:
            outfile = os.path.join(output_dir, t.get_path(limit=limit))
            write_page(
                "tag", outfile, tag=t, **standard_args,
            )
            add_touched(outfile)

        # Generate all-tags template
        tagfile = os.path.join(output_dir, models_db.Tag.get_path_all(limit))
        write_page("tags", tagfile, tags=tags, **standard_args)
        add_touched(tagfile)

        # Generate species templates
        specdir = os.path.join(output_dir, "_species")
        if not os.path.exists(specdir):
            os.makedirs(specdir)

        species = list(models_db.Species.get_all(limit=limit))
        for spec in species:
            outfile = os.path.join(output_dir, spec.get_path(limit=limit))
            write_page("species", outfile, species=spec, **standard_args)
            add_touched(outfile)

        # Generate all-species template
        specfile = os.path.join(output_dir, models_db.Species.get_path_all(limit))
        write_page(
            "species_all", specfile, species=species, **standard_args,
        )
        add_touched(specfile)

        # Generate group templates
        groupdir = os.path.join(output_dir, "_groups")
        if not os.path.exists(groupdir):
            os.makedirs(groupdir)

        groups = list(models_db.Group.get_all(limit=limit))
        for group in groups:
            outfile = os.path.join(output_dir, group.get_path(limit=limit))
            write_page("group", outfile, group=group, **standard_args)
            add_touched(outfile)

        # Generate character templates
        chardir = os.path.join(output_dir, "_characters")
        if not os.path.exists(chardir):
            os.makedirs(chardir)

        characters = list(models_db.Character.get_all(limit=limit))
        for char in characters:
            outfile = os.path.join(output_dir, char.get_path(limit=limit))
            write_page("character", outfile, character=char, **standard_args)
            add_touched(outfile)

        # Generate all-characters template
        charfile = os.path.join(output_dir, models_db.Character.get_path_all(limit))
        write_page("characters", charfile, characters=characters, **standard_args)
        add_touched(charfile)

        # # Generate JSON file
        # jsondata = {
        #     "data": use_artists,
        #     "tags": use_tags,
        #     "tag_descriptions": data.tag_key,
        #     "groups": use_groups,
        #     "species": use_species,
        #     "species_descriptions": data.species_key,
        #     "characters": use_chars,
        #     "thumbnails": thumbnails,
        # }

        # jsonfile = os.path.join(
        #     output_dir, build_filename("data", extension="json", limit=limit)
        # )
        # utils.write_json(jsonfile, jsondata, True)
        # add_touched(jsonfile)

        # Generate index file
        indexdata = {
            "pathing": pathing,
            "limit": limit,
            "thumbnails": thumbnails,
            "submissions": submissions,
            "artists": artists,
            "tags": tags,
            "groups": groups,
            "species": species,
            "characters": characters,
        }

        indexfile = os.path.join(output_dir, build_filename("index", limit=limit))
        write_page("index", indexfile, **indexdata)
        add_touched(indexfile)

    cleanup_dead_files(output_dir, tree_hash, touched_files)


if __name__ == "__main__":
    args = utils.parse_args()
    limit = utils.get_limit_from_args(args)
    generate_static_site(args.indir, args.outdir, limit=limit, force=args.force)
    print("Files written.")
