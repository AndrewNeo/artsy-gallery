from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


class InternalLinksExtension(Extension):
    def __init__(self, *args, **kwargs):
        super(InternalLinksExtension, self).__init__(*args, **kwargs)

    def extendMarkdown(self, md, md_globals):
        LINK_RE = r"<(a|c):([^>]+)>"
        md.inlinePatterns.add("ilink", InternalLinks(LINK_RE), "<escape")


class InternalLinks(Pattern):
    def __init__(self, pattern):
        super(InternalLinks, self).__init__(pattern)

    def handleMatch(self, m):
        # <a:artist|Artist>
        linktype = m.group(2)
        linkcat = "characters"
        if linktype == "a":
            linkcat = "/{}/"
        elif linktype == "c":
            linkcat = "/_characters/{}.html"
        else:
            return "`unresolved link`"

        inner = m.group(3).split("|")
        linkdest = linktext = inner[0]
        if len(inner) > 1:
            linktext = inner[1]

        a = etree.Element("a")
        a.text = linktext
        a.set("href", linkcat.format(linkdest))  # TODO: Pull full names from config
        return a
