import os
import glob
import json
import argparse
import binascii
import attr
import cattr
from typing import Optional


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
    parser.add_argument("-vi", "--visibility", help="Set output visibility", default=None)
    parser.add_argument("--visibilityOnly", help="Restrict output to visibility level", action="store_true")
    parser.add_argument("-lo", "--lockout", help="Set output lockout", default=None)
    parser.add_argument("--lockoutOnly", help="Restrict output to lockout level", action="store_true")
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
            if "visibility" in config:
                args.visibility = config["visibility"]
            if "visibilityOnly" in config:
                args.visibilityOnly = config["visibilityOnly"]
            if "lockout" in config:
                args.lockout = config["lockout"]
            if "lockoutOnly" in config:
                args.lockoutOnly = config["lockoutOnly"]
            if "force" in config:
                args.force = config["force"]

    if not args.indir:
        raise RuntimeError("Missing input directory.")

    return args


@attr.s
class LimitFilter(object):
    visibility = cattr.typed(Optional[str], default=None)
    visibilityOnly = cattr.typed(Optional[bool], default=False)
    lockout = cattr.typed(Optional[str], default=None)
    lockoutOnly = cattr.typed(Optional[bool], default=False)

    def is_visible(self, f):
        if (self.visibility == "*") or (not self.visibilityOnly and f.visibility is None) or (f.visibility == self.visibility):
            if (self.lockout == "*") or (not self.lockoutOnly and f.lockout is None) or (f.lockout == self.lockout):
                return True

        return False


def get_limit_from_args(args):
    return LimitFilter(
        visibility=args.visibility,
        visibilityOnly=args.visibilityOnly,
        lockout=args.lockout,
        lockoutOnly=args.lockoutOnly
    )
