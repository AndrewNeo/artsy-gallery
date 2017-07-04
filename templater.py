from jinja2 import Environment, FileSystemLoader

class Templater(object):
    '''Build templates.'''

    def __init__(self, template_dir):
        self.jinja = Environment(loader=FileSystemLoader(template_dir))

    def generate(self, template_name, **kwargs):
        '''Generate an output file given the template name and content.'''
        template = self.jinja.get_template("%s.html" % (template_name))
        return template.render(**kwargs)
