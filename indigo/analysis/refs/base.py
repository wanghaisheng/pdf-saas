from lxml import etree
import re

from indigo.plugins import LocaleBasedMatcher, plugins


class BaseRefsFinder(LocaleBasedMatcher):
    """ Finds references to Acts in documents.

    Subclasses must implement `find_references_in_document`.
    """

    act_re = None
    """ This must be defined by a subclass. It should be a compiled regular
    expression, with named captures for `ref`, `num` and `year`.
    """
    candidate_xpath = None  # this must be defined by a subclass

    # the ancestor elements that can contain references
    ancestors = ['coverpage', 'preface', 'preamble', 'body', 'mainBody', 'conclusions']

    def find_references_in_document(self, document):
        """ Find references in +document+, which is an Indigo Document object.
        """
        # we need to use etree, not objectify, so we can't use document.doc.root,
        # we have to re-parse it
        root = etree.fromstring(document.content)
        self.frbr_uri = document.doc.frbr_uri
        self.setup(root)
        self.find_references(root)
        document.content = etree.tostring(root, encoding='utf-8').decode('utf-8')

    def setup(self, root):
        self.ns = root.nsmap[None]
        self.nsmap = {'a': self.ns}
        self.ref_tag = "{%s}ref" % self.ns

        self.ancestor_xpath = etree.XPath('|'.join('.//a:%s' % a for a in self.ancestors), namespaces=self.nsmap)
        self.candidate_xpath = etree.XPath(self.candidate_xpath, namespaces=self.nsmap)

    def make_href(self, match):
        """ Turn this match into a full FRBR URI href
        """
        return '/%s/act/%s/%s' % (self.frbr_uri.country, match.group('year'), match.group('num'))

    def find_references(self, root):
        for root in self.ancestor_nodes(root):
            for candidate in self.candidate_nodes(root):
                node = candidate.getparent()

                if not candidate.is_tail:
                    # text directly inside a node
                    match = self.act_re.search(node.text)
                    if match:
                        # mark the reference and continue to check the new tail
                        node = self.mark_reference(node, match, in_tail=False)

                while node is not None and node.tail:
                    match = self.act_re.search(node.tail)
                    if not match:
                        break

                    # mark the reference and continue to check the new tail
                    node = self.mark_reference(node, match, in_tail=True)

    def mark_reference(self, node, match, in_tail):
        ref, start_pos, end_pos = self.make_ref(match)

        if in_tail:
            node.addnext(ref)
            node.tail = match.string[:start_pos]
            ref.tail = match.string[end_pos:]
        else:
            node.text = match.string[:start_pos]
            node.insert(0, ref)
            ref.tail = match.string[end_pos:]

        return ref

    def make_ref(self, match):
        """ Make a reference out of this match, returning a (ref, start, end) tuple
        which is the new ref node, and the start and end position of what text
        in the parent element it should be replacing.

        By default, the first group in the `act_re` is substituted with the ref.
        """
        ref = etree.Element(self.ref_tag)
        ref.text = match.group('ref')
        ref.set('href', self.make_href(match))
        return (ref, match.start('ref'), match.end('ref'))

    def ancestor_nodes(self, root):
        for x in self.ancestor_xpath(root):
            yield x

    def candidate_nodes(self, root):
        for x in self.candidate_xpath(root):
            yield x


@plugins.register('refs')
class RefsFinderENG(BaseRefsFinder):
    """ Finds references to Acts in documents, of the form:

        Act 52 of 2001
        Act no. 52 of 1998
        Income Tax Act, 1962 (No 58 of 1962)

    """

    # country, language, locality
    locale = (None, 'eng', None)

    act_re = re.compile(
        r'''\bAct,?\s+
            (\d{4}\s+)?
            \(?
            (?P<ref>
             ([nN]o\.?\s*)?
             (?P<num>\d+)\s+
             of\s+
             (?P<year>\d{4})
            )
        ''', re.X)
    candidate_xpath = ".//text()[contains(., 'Act') and not(ancestor::a:ref)]"


class BaseInternalRefsFinder(LocaleBasedMatcher):
    """ Finds internal references in documents, such as to sections.
    """

    section_re = None
    """ This must be defined by a subclass. It should be a compiled regular
    expression, with named captures for `ref` and `num`.
    """
    candidate_xpath = None
    """ Xpath for candidate text nodes that should be tested for references.
    Must be defined by a subclass.
    """

    # the ancestor elements that can contain references
    ancestors = ['body', 'mainBody', 'conclusions']

    def find_references_in_document(self, document):
        """ Find references in +document+, which is an Indigo Document object.
        """
        # we need to use etree, not objectify, so we can't use document.doc.root,
        # we have to re-parse it
        root = etree.fromstring(document.content)
        self.setup(root)
        self.find_references(root)
        document.content = etree.tostring(root, encoding='utf-8').decode('utf-8')

    def setup(self, root):
        self.ns = root.nsmap[None]
        self.nsmap = {'a': self.ns}
        self.ref_tag = f'{{{self.ns}}}ref'
        self.ancestor_xpath = etree.XPath('|'.join(f'.//a:{a}' for a in self.ancestors), namespaces=self.nsmap)
        self.candidate_xpath = etree.XPath(self.candidate_xpath, namespaces=self.nsmap)

    def find_references(self, root):
        for ancestor in self.ancestor_nodes(root):
            for candidate in self.candidate_nodes(ancestor):
                node = candidate.getparent()

                if not candidate.is_tail:
                    # text directly inside a node
                    for match in self.section_re.finditer(node.text):
                        if self.is_valid(node, match):
                            # mark the reference and continue to check the new tail
                            node = self.mark_reference(node, match, in_tail=False)
                            break

                while node is not None and node.tail:
                    for match in self.section_re.finditer(node.tail):
                        if self.is_valid(node, match):
                            # mark the reference and continue to check the new tail
                            node = self.mark_reference(node, match, in_tail=True)
                            break

                    else:
                        # we didn't break out of the loop, so there are no valid matches, give up
                        node = None

    def is_valid(self, node, match):
        return self.find_target(node, match) is not None

    def find_target(self, node, match):
        """ Return the target element that this reference targets.
        """
        raise NotImplementedError()

    def mark_reference(self, node, match, in_tail):
        ref, start_pos, end_pos = self.make_ref(node, match)

        if in_tail:
            node.addnext(ref)
            node.tail = match.string[:start_pos]
            ref.tail = match.string[end_pos:]
        else:
            node.text = match.string[:start_pos]
            node.insert(0, ref)
            ref.tail = match.string[end_pos:]

        return ref

    def make_ref(self, node, match):
        """ Make a reference out of this match, returning a (ref, start, end) tuple
        which is the new ref node, and the start and end position of what text
        in the parent element it should be replacing.
        """
        ref = etree.Element(self.ref_tag)
        ref.text = match.group('ref')
        ref.set('href', self.make_href(node, match))
        return ref, match.start('ref'), match.end('ref')

    def make_href(self, node, match):
        """ Return the target href for this match.
        """
        raise NotImplementedError()

    def ancestor_nodes(self, root):
        for x in self.ancestor_xpath(root):
            yield x

    def candidate_nodes(self, root):
        for x in self.candidate_xpath(root):
            yield x


@plugins.register('internal-refs')
class SectionRefsFinderENG(BaseInternalRefsFinder):
    """ Finds internal references to sections in documents, of the form:

        section 26
        section 26B
        TODO: match subsections
        TODO: match paragraphs
        TODO: match multiple sections
        TODO: match ranges of sections
    """

    # country, language, locality
    locale = (None, 'eng', None)

    section_re = re.compile(
        r'''
        (?P<ref>
          \b[sS]ections?\s+
          (?P<num>\d+[A-Z]*)
        )
        (?P<subsection_ref>\s*\(\d+[A-Z]*\))?
        (?P<paragraph_ref>\s*\([a-z]+[A-Z]*\))?
        (?P<subparagraph_ref>\s*\([ivx]+[A-Z]*\))?
        (?P<item_ref>\s*\([a-z]{2,}[A-Z]*\))?
        (?!\s*\()
        (\s+of\s+(this\s+Act|the\s+|Act\s+)?)?
        ''',
        re.X)

    candidate_xpath = ".//text()[contains(., 'section') and not(ancestor::a:ref)]"
    match_cache = {}

    def is_valid(self, node, match):
        # check that it's not an external reference
        ref = match.group(0)
        if ref.endswith('the ') or ref.endswith('Act '):
            return False

        return super().is_valid(node, match)

    def find_target(self, node, match):
        num = match.group('num')
        candidate_elements = node.xpath(f"//a:section[a:num[text()='{num}.']]", namespaces=self.nsmap)
        if candidate_elements:
            self.match_cache[num] = candidate_elements[0]
            return candidate_elements[0]

    def make_href(self, node, match):
        target = self.match_cache[match.group('num')]
        return '#' + target.get('id')
