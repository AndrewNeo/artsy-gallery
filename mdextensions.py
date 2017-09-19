from markdown.extensions import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree


class InternalLinksExtension(Extension):
    def __init__(self, *args, **kwargs):
        super(InternalLinksExtension, self).__init__(*args, **kwargs)

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.add("ilalink", TopLevelLinks(r"<a:([^>]+)>", "/{}/"), "<escape")
        md.inlinePatterns.add("ilclink", TopLevelLinks(r"<c:([^>]+)>", "/_characters/{}.html"), "<escape")
        md.inlinePatterns.add("ilslink", SlugLinks(r"<s:(\w+):([^>]+)>", "/{0}/{1}.html"), "<escape")


class TopLevelLinks(Pattern):
    def __init__(self, pattern, fmt):
        super(TopLevelLinks, self).__init__(pattern)
        self.fmt = fmt

    def handleMatch(self, m):
        # <a:artist|Artist>
        inner = m.group(2).split("|")
        linkdest = linktext = inner[0]
        if len(inner) > 1:
            linktext = inner[1]

        a = etree.Element("a")
        a.text = linktext
        a.set("href", self.fmt.format(linkdest))  # TODO: Pull full names from config
        return a


class SlugLinks(Pattern):
    def __init__(self, pattern, fmt):
        super(SlugLinks, self).__init__(pattern)
        self.fmt = fmt

    def handleMatch(self, m):
        # <s:artist:slug|Artist>
        artist = m.group(2)
        inner = m.group(3).split("|")
        slug = linktext = inner[0]
        if len(inner) > 1:
            linktext = inner[1]

        a = etree.Element("a")
        a.text = linktext
        a.set("href", self.fmt.format(artist, slug))  # TODO: Pull full title from config
        return a
