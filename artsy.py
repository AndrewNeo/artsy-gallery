#!/usr/bin/env python3
'''Artsy, an artsy sort of gallery.'''

import os
import shutil
import glob
from collections import OrderedDict
from resizeimage import resizeimage
from PIL import Image
from data import get_art_data
from templater import Templater
import utils


templater = Templater("templates")


def generate_thumbnail_size(img, width, filename):
    thumb = resizeimage.resize_thumbnail(img, [width, width])
    thumb.save(filename, img.format)


def generate_thumbnails(indir, outdir, image, widths, do_update, add_touched, force=False):
    thumbnails = {}
    relpath = os.path.join(indir, image.filename)

    def get_path(size):
        return os.path.join(outdir, "{slug}_{size}.{imgext}".format(size=size, slug=image.slug, imgext=image.get_file_ext()))

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


def write_page(template, outfile, **kwargs):
    with open(outfile, "w") as f:
        td = templater.generate(template, **kwargs)
        f.write(td)


def cleanup_dead_files(output_dir, tree_hash, touched_files):
    dead_files = set(tree_hash.keys()) - set(touched_files)

    for df in dead_files:
        print("Deleting file {}".format(df))
        os.remove(os.path.join(output_dir, df))


# TODO: Don't update files that don't need updating
def generate_static_site(input_dir, output_dir, limit="*", force=False):
    '''Output templates to filesystem.'''
    # Get data and fail on error
    data = get_art_data(input_dir, limit)

    touched_files = []

    def add_touched(filename):
        touched_files.append(utils.remove_parent_path(output_dir, filename))

    def do_update(fullpath, fullhash):
        return force or not os.path.exists(fullpath) or fullpath not in tree_hash or fullhash != tree_hash[fullpath]

    tree_hash = {}

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
            thumbnails[image.slug] = generate_thumbnails(artist_file._reldir, artistdir, image, [120, 512], do_update, add_touched)

            # Write templated file
            write_page("image", outfile, artist=artist, image=image, get_character_breakdown=data.get_character_breakdown, get_species_details=data.get_species_details, get_tag_details=data.get_tag_details, sequence=data.get_sequence(image), thumbnails=thumbnails[image.slug])
            add_touched(outfile)

            artistout["files"].append(image)

        # Generate artist templates
        artistfile = os.path.join(output_dir, artist.get_slug(), "index.html")

        # Write templated file
        write_page("artist", artistfile, artist=artist, files=files, thumbnails=thumbnails)
        add_touched(artistfile)

        use_artists.append(artistout)

    # Generate all-artists template
    artistsfile = os.path.join(output_dir, "all_artists.html")
    write_page("artists", artistsfile, artists=use_artists, limit=limit, thumbnails=thumbnails)
    add_touched(artistsfile)

    # Generate tag templates
    use_tags = list(sorted(data.get_all_tags(limit=limit, ignore="species")))

    tagsdir = os.path.join(output_dir, "_tags")
    if not os.path.exists(tagsdir):
        os.makedirs(tagsdir)

    collected_tags = OrderedDict()
    for t in use_tags:
        files = data.get_files_by_tag(t, limit=limit)
        collected_tags[t] = files

        outfile = os.path.join(tagsdir, "{}.html".format(t.replace("#", "_")))
        write_page("tag", outfile, tag=t, description=data.get_tag_details(t), files=files, thumbnails=thumbnails)
        add_touched(outfile)

    # Generate all-tags template
    tagfile = os.path.join(output_dir, "all_tags.html")
    write_page("tags", tagfile, tags=collected_tags, thumbnails=thumbnails, get_tag_details=data.get_tag_details)
    add_touched(tagfile)

    # Generate species templates
    use_species = list(sorted(data.get_all_species(limit=limit)))

    specdir = os.path.join(output_dir, "_species")
    if not os.path.exists(specdir):
        os.makedirs(specdir)

    collected_species = OrderedDict()
    for spec in use_species:
        files = data.get_files_by_species(spec, limit=limit)
        collected_species[spec] = files

        outfile = os.path.join(specdir, "{}.html".format(spec))
        write_page("species", outfile, species=spec, description=data.get_species_details(spec), files=files, thumbnails=thumbnails)
        add_touched(outfile)

    # Generate all-species template
    specfile = os.path.join(output_dir, "all_species.html")
    write_page("species_all", specfile, species=collected_species, thumbnails=thumbnails, get_species_details=data.get_species_details)
    add_touched(specfile)

    # Collect unique characters
    # TODO: Sort this by the character metadata definition
    chars = list(sorted(set(map(lambda x: x.split("#")[0], data.get_all_characters(limit=limit)))))
    use_chars = {cn: data.get_character_details(cn) for cn in chars}

    # Generate character templates
    chardir = os.path.join(output_dir, "_characters")
    if not os.path.exists(chardir):
        os.makedirs(chardir)

    collected_chars = OrderedDict()
    for char_name, char in use_chars.items():
        files = data.get_files_by_character(char_name, limit=limit)
        thischar = {"character": char, "files": files, "species": {}}
        thischarspec = thischar["species"]
        collected_chars[char_name] = thischar

        for sn, s in char.species.items():
            sf = data.get_files_by_character(char_name, species=sn, ignore_subforms=True, limit=limit)

            if len(sf) > 0 or s.subforms:
                thischarspec[sn] = {"species": s, "files": sf, "subforms": {}}

            if s.subforms:
                for sfn, sf in s.subforms.items():
                    sff = data.get_files_by_character(char_name, species=sn, subform=sfn, limit=limit)

                    if len(sff) > 0:
                        thischarspec[sn]["subforms"][sfn] = {"subform": sf, "files": sff}

        outfile = os.path.join(chardir, "{}.html".format(char_name))
        write_page("character", outfile, data=thischar, thumbnails=thumbnails, get_species_details=data.get_species_details)
        add_touched(outfile)

    # Generate all-characters template
    charfile = os.path.join(output_dir, "all_characters.html")
    write_page("characters", charfile, characters=collected_chars, thumbnails=thumbnails)
    add_touched(charfile)

    # Generate JSON file
    jsonfile = os.path.join(output_dir, "data.json")
    jsondata = {
        "data": use_artists,
        "tags": use_tags,
        "tag_descriptions": data.tag_key,
        "species": use_species,
        "species_descriptions": data.species_key,
        "characters": use_chars,
        "thumbnails": thumbnails
    }

    utils.write_json(jsonfile, jsondata, True)
    add_touched(jsonfile)

    # Generate index file
    indexfile = os.path.join(output_dir, "index.html")
    indexdata = {
        "limit": limit,
        "thumbnails": thumbnails,
        "files": data.get_all_files(limit=limit),  # Called manually here to sort the entire thing
        "artists": map(lambda x: x["artist"], use_artists),
        "tags": use_tags,
        "species": use_species,
        "characters": list(sorted(chars)),
        "character_data": use_chars,
        "get_tag_details": data.get_tag_details,
        "get_species_details": data.get_species_details
    }

    write_page("index", indexfile, **indexdata)
    add_touched(indexfile)

    cleanup_dead_files(output_dir, tree_hash, touched_files)


if __name__ == "__main__":
    args = utils.parse_args()
    generate_static_site(args.indir, args.outdir, args.limit, force=args.force)
    print("Files written.")
