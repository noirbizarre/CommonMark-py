from __future__ import unicode_literals


import re
from builtins import str
from CommonMark.common import escape_xml
from CommonMark.render.renderer import Renderer


reUnsafeProtocol = re.compile(
    r'^javascript:|vbscript:|file:|data:', re.IGNORECASE)
reSafeDataProtocol = re.compile(
    r'^data:image\/(?:png|gif|jpeg|webp)', re.IGNORECASE)


def potentially_unsafe(url):
    return re.match(reUnsafeProtocol, url) and \
        (not re.match(reSafeDataProtocol, url))


class HtmlRenderer(Renderer):
    def __init__(self, options={}):
        #  by default, soft breaks are rendered as newlines in HTML
        options['softbreak'] = options.get('softbreak') or '\n'
        # set to "<br />" to make them hard breaks
        # set to " " if you want to ignore line wrapping in source

        self.disable_tags = 0
        self.last_out = '\n'
        self.options = options

    def escape(self, text, preserve_entities):
        return escape_xml(text, preserve_entities)

    def tag(self, name, attrs=None, selfclosing=None):
        """Helper function to produce an HTML tag."""
        if self.disable_tags > 0:
            return

        self.buf += '<' + name
        if attrs and len(attrs) > 0:
            for attrib in attrs:
                self.buf += ' ' + attrib[0] + '="' + attrib[1] + '"'

        if selfclosing:
            self.buf += ' /'

        self.buf += '>'
        self.last_out = '>'

    # Node methods #

    def text(self, node, entering=None):
        self.out(node.literal)

    def softbreak(self, node=None, entering=None):
        self.lit(self.options['softbreak'])

    def linebreak(self, node=None, entering=None):
        self.tag('br', [], True)
        self.cr()

    def link(self, node, entering):
        attrs = self.attrs(node)
        if entering:
            if not (self.options.get('safe') and
                    potentially_unsafe(node.destination)):
                attrs.append(['href', self.escape(node.destination, True)])

            if node.title:
                attrs.append(['title', self.escape(node.title, True)])

            self.tag('a', attrs)
        else:
            self.tag('/a')

    def image(self, node, entering):
        if entering:
            if self.disable_tags == 0:
                if self.options.get('safe') and \
                   potentially_unsafe(node.destination):
                    self.lit('<img src="" alt="')
                else:
                    self.lit('<img src="' +
                             self.escape(node.destination, True) +
                             '" alt="')
            self.disable_tags += 1
        else:
            self.disable_tags -= 1
            if self.disable_tags == 0:
                if node.title:
                    self.lit('" title="' + self.escape(node.title, True))
                self.lit('" />')

    def emph(self, node, entering):
        self.tag('em' if entering else '/em')

    def strong(self, node, entering):
        self.tag('strong' if entering else '/strong')

    def paragraph(self, node, entering):
        grandparent = node.parent.parent
        attrs = self.attrs(node)
        if grandparent is not None and grandparent.t == 'list':
            if grandparent.list_data['tight']:
                return

        if entering:
            self.cr()
            self.tag('p', attrs)
        else:
            self.tag('/p')
            self.cr()

    def heading(self, node, entering):
        tagname = 'h' + str(node.level)
        attrs = self.attrs(node)
        if entering:
            self.cr()
            self.tag(tagname, attrs)
        else:
            self.tag('/' + tagname)
            self.cr()

    def code(self, node, entering):
        self.tag('code')
        self.out(node.literal)
        self.tag('/code')

    def code_block(self, node, entering):
        info_words = node.info.split() if node.info else []
        attrs = self.attrs(node)
        if len(info_words) > 0 and len(info_words[0]) > 0:
            attrs.append(['class', 'language-' +
                          self.escape(info_words[0], True)])

        self.cr()
        self.tag('pre')
        self.tag('code', attrs)
        self.out(node.literal)
        self.tag('/code')
        self.tag('/pre')
        self.cr()

    def thematic_break(self, node, entering):
        attrs = self.attrs(node)
        self.cr()
        self.tag('hr', attrs, True)
        self.cr()

    def block_quote(self, node, entering):
        attrs = self.attrs(node)
        if entering:
            self.cr()
            self.tag('blockquote', attrs)
            self.cr()
        else:
            self.cr()
            self.tag('/blockquote')
            self.cr()

    def list(self, node, entering):
        tagname = 'ul' if node.list_data['type'] == 'bullet' else 'ol'
        attrs = self.attrs(node)
        if entering:
            start = node.list_data['start']
            if start is not None and start != 1:
                attrs.append(['start', str(start)])

            self.cr()
            self.tag(tagname, attrs)
            self.cr()
        else:
            self.cr()
            self.tag('/' + tagname)
            self.cr()

    def item(self, node, entering):
        attrs = self.attrs(node)
        if entering:
            self.tag('li', attrs)
        else:
            self.tag('/li')
            self.cr()

    def html_inline(self, node, entering):
        if self.options.get('safe'):
            self.lit('<!-- raw HTML omitted -->')
        else:
            self.lit(node.literal)

    def html_block(self, node, entering):
        self.cr()
        if self.options.get('safe'):
            self.lit('<!-- raw HTML omitted -->')
        else:
            self.lit(node.literal)
        self.cr()

    def custom_inline(self, node, entering):
        if entering and node.on_enter:
            self.lit(node.on_enter)
        elif (not entering) and node.on_exit:
            self.lit(node.on_exit)

    def custom_block(self, node, entering):
        self.cr()
        if entering and node.on_enter:
            self.lit(node.on_enter)
        elif (not entering) and node.on_exit:
            self.lit(node.on_exit)
        self.cr()

    # Helper methods #

    def out(self, s):
        self.lit(self.escape(s, False))

    def attrs(self, node):
        att = []
        if self.options.get('sourcepos'):
            pos = node.sourcepos
            if pos:
                att.append(['data-sourcepos', str(pos[0][0]) + ':' +
                            str(pos[0][1]) + '-' + str(pos[1][0]) + ':' +
                            str(pos[1][1])])

        return att
