import os
import glob
import json
import argparse
import binascii
import cattr


def remove_parent_path(parent, filepath):
    return filepath[len(parent) + 1:]


def get_hash(infile):
    if not os.path.exists(infile):
        return None

    return "%08X" % (binascii.crc32(open(infile, "rb").read()) & 0xFFFFFFFF)


def get_dir_hashes(indir):
    files = glob.iglob("{}/**".format(indir), recursive=True)
    return {remove_parent_path(indir, f): get_hash(f) for f in files if os.path.isfile(f)}


# https://stackoverflow.com/a/27974027/151495
def clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, clean_empty(v)) for k, v in d.items()) if v}


def write_json(outfile, data, clean=False):
    if clean:
        data = clean_empty(cattr.unstructure(data))

    with open(outfile, "w") as f:
        json.dump(data, f)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--indir", help="Input directory", default=None, metavar="INPUT_DIR")
    parser.add_argument("-o", "--outdir", help="Output directory", default="output", metavar="OUTPUT_DIR")
    parser.add_argument("-l", "--limit", help="Set output limit", default=None)
    parser.add_argument("-f", "--force", help="Force rewrite content", action="store_true")
    parser.add_argument("-c", "--config", help="Configuration file", default=None, metavar="FILENAME")

    args = parser.parse_args()

    if args.config:
        with open(args.config, "r") as f:
            config = json.loads(f.read())
            if "indir" in config:
                args.indir = config["indir"]
            if "outdir" in config:
                args.outdir = config["outdir"]
            if "limit" in config:
                args.limit = config["limit"]
            if "force" in config:
                args.force = config["force"]

    return args
