from jinja2 import Environment, FileSystemLoader, Markup
from markdown import Markdown
from mdextensions import InternalLinksExtension


class Templater(object):
    '''Build templates.'''

    def __init__(self, template_dir):
        self.md = Markdown(extensions=[
            'markdown.extensions.nl2br',
            InternalLinksExtension()
        ])

        self.jinja = Environment(loader=FileSystemLoader(template_dir))
        self.jinja.filters["markdown"] = lambda text: Markup(self.md.convert(text))

    def generate(self, template_name, **kwargs):
        '''Generate an output file given the template name and content.'''
        template = self.jinja.get_template("%s.html" % (template_name))
        return template.render(**kwargs)
