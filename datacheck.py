'''Some data integrity checks.'''

from data import get_art_data
import utils


def log_has_self_link(ref, links):
    if not links or (not links.fa and not links.weasyl):
        print("Missing self link in {}".format(ref.filename))


def log_dup_links(cached, ref, links):
    if not links:
        return

    if links.fa:
        if links.fa in cached["fa"]:
            print("Duplicate FA link found in {}".format(ref.filename))
        else:
            cached["fa"].add(links.fa)

    if links.weasyl:
        if links.weasyl in cached["weasyl"]:
            print("Duplicate Weasyl link found in {}".format(ref.filename))
        else:
            cached["weasyl"].add(links.weasyl)


def log_near_empty_tags(tag, files):
    if len(files) < 2 and not tag.startswith("species#"):
        print("Tag {} has {} entries".format(tag, len(files)))


def check(data):
    links = {"fa": set(), "weasyl": set()}

    for f in data.get_all_files():
        log_has_self_link(f, f.my_links)
        log_dup_links(links, f, f.my_links)
        log_dup_links(links, f, f.artist_links)

    for t in data.get_all_tags():
        log_near_empty_tags(t, data.get_files_by_tag(t))


if __name__ == "__main__":
    args = utils.parse_args()
    data = get_art_data(args.indir, None)

    # TODO: Handle severity / classifications
    check(data)
