'''Some data integrity checks.'''

from data import get_art_data
import utils


def log_dup_slugs(el, cached, ref):
    if ref.slug in cached:
        el["error"].append("Duplicate slug found in {}".format(ref.filename))
    else:
        cached.add(ref.slug)


def log_has_self_link(el, ref, links):
    if not links or (not links.fa and not links.weasyl):
        el["warn"].append("Missing self link in {}".format(ref.filename))


def log_dup_links(el, cached, ref, links):
    if not links:
        return

    if links.fa:
        if links.fa in cached["fa"]:
            el["error"].append("Duplicate FA link found in {}".format(ref.filename))
        else:
            cached["fa"].add(links.fa)

    if links.weasyl:
        if links.weasyl in cached["weasyl"]:
            el["error"].append("Duplicate Weasyl link found in {}".format(ref.filename))
        else:
            cached["weasyl"].add(links.weasyl)


def log_near_empty_tags(el, tag, files):
    if len(files) < 2 and not tag.startswith("species#"):
        el["info"].append("Tag {} has {} entries".format(tag, len(files)))


def check(data):
    el = {"info": [], "warn": [], "error": []}
    slugs = set()
    links = {"fa": set(), "weasyl": set()}

    for f in data.get_all_files():
        log_dup_slugs(el, slugs, f)
        log_has_self_link(el, f, f.my_links)
        log_dup_links(el, links, f, f.my_links)
        log_dup_links(el, links, f, f.artist_links)

    for t in data.get_all_tags():
        log_near_empty_tags(el, t, data.get_files_by_tag(t))

    return el


def printout(r, cat, prefix):
    if len(r[cat]) > 0:
        for l in r[cat]:
            print("{}: {}".format(prefix, l))


if __name__ == "__main__":
    args = utils.parse_args()
    data = get_art_data(args.indir, None)

    results = check(data)
    printout(results, "error", "ERROR")
    printout(results, "warn", "WARN")
    printout(results, "info", "INFO")
