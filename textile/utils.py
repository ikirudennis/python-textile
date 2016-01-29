try:
    import regex as re
except ImportError:
    import re

try:
    # Python 3
    from urllib.parse import urlparse
    from html.parser import HTMLParser
    xrange = range
    unichr = chr
    unicode = str
except ImportError:
    # Python 2
    from urlparse import urlparse
    from HTMLParser import HTMLParser

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from xml.etree import ElementTree

from textile.regex_strings import valign_re_s, halign_re_s


def normalize_newlines(string):
    out = string.strip()
    out = re.sub(r'\r\n', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    out = re.sub(r'\n\s*\n', '\n\n', out)
    out = re.sub(r'"$', '" ', out)
    return out

def has_raw_text(text):
    """checks whether the text has text not already enclosed by a block tag"""
    # The php version has orders the below list of tags differently.  The
    # important thing to note here is that the pre must occur before the p or
    # else the regex module doesn't properly match pre-s. It only matches the
    # p in pre.
    r = re.compile(r'<(pre|p|blockquote|div|form|table|ul|ol|dl|h[1-6])[^>]*?>.*</\1>',
                   re.S).sub('', text.strip()).strip()
    r = re.compile(r'<(hr|br)[^>]*?/>').sub('', r)
    return '' != r

def list_type(list_string):
    listtypes = {
        list_string.startswith('*'): 'u',
        list_string.startswith('#'): 'o',
        (not list_string.startswith('*') and not list_string.startswith('#')):
        'd'
    }
    return listtypes.get(True, False)

def is_rel_url(url):
    """Identify relative urls."""
    (scheme, netloc) = urlparse(url)[0:2]
    return not scheme and not netloc

def encode_high(text):
    """Encode the text so that it is an appropriate HTML entity."""
    return ord(text)

def decode_high(text):
    """Decode encoded HTML entities."""
    h = HTMLParser()
    text = '&#{0};'.format(text)
    return h.unescape(text)

def encode_html(text, quotes=True):
    """Return text that's safe for an HTML attribute."""
    a = (
        ('&', '&amp;'),
        ('<', '&lt;'),
        ('>', '&gt;'))

    if quotes:
        a = a + (("'", '&#39;'),
                 ('"', '&#34;'))

    for k, v in a:
        text = text.replace(k, v)
    return text

def generate_tag(tag, content, attributes):
    """Generate a complete html tag using the ElementTree module.  tag and
    content are strings, the attributes argument is a dictionary."""
    content = unicode(content).encode('utf-8')
    element = ElementTree.Element(tag, attrib=attributes)
    element_tag = ElementTree.tostring(element)
    # FIXME: Kind of an ugly hack.  There *must* be a cleaner way.  I tried
    # adding text by assigning it to a.text.  That results in non-ascii text
    # being html-entity encoded.  Not bad, but not entirely matching
    # php-textile either.
    #
    # I thought I had found a fancy solution, using ElementTree.tostringlist,
    # but it fails differently on different platforms.
    element_tag = unicode(element_tag).encode('utf-8').rstrip(' />')
    element_text = '{0}>{1}</{2}>'.format(element_tag, content, tag)
    return unicode(element_text).decode('utf-8')

def is_valid_url(url):
    parsed = urlparse(url)
    if parsed.scheme == '':
        return True
    return False

def pba(block_attributes, element=None, include_id=True):
    """Parse block attributes."""
    attrs = parse_attributes(block_attributes, element, include_id)
    if not attrs:
        return ''
    result = ' '.join(['{0}="{1}"'.format(k, v) for k, v in attrs.items()])
    return ' {0}'.format(result)

def parse_attributes(block_attributes, element=None, include_id=True):
    vAlign = {'^': 'top', '-': 'middle', '~': 'bottom'}
    hAlign = {'<': 'left', '=': 'center', '>': 'right', '<>': 'justify'}
    style = []
    aclass = ''
    lang = ''
    colspan = ''
    rowspan = ''
    block_id = ''
    span = ''
    width = ''
    result = OrderedDict()

    if not block_attributes:
        return result

    matched = block_attributes
    if element == 'td':
        m = re.search(r'\\(\d+)', matched)
        if m:
            colspan = m.group(1)

        m = re.search(r'/(\d+)', matched)
        if m:
            rowspan = m.group(1)

    if element == 'td' or element == 'tr':
        m = re.search(r'({0})'.format(valign_re_s), matched)
        if m:
            style.append("vertical-align:{0}".format(vAlign[m.group(1)]))

    m = re.search(r'\{([^}]*)\}', matched)
    if m:
        style.extend(m.group(1).rstrip(';').split(';'))
        matched = matched.replace(m.group(0), '')

    m = re.search(r'\[([^\]]+)\]', matched, re.U)
    if m:
        lang = m.group(1)
        matched = matched.replace(m.group(0), '')

    m = re.search(r'\(([^()]+)\)', matched, re.U)
    if m:
        aclass = m.group(1)
        matched = matched.replace(m.group(0), '')

    m = re.search(r'([(]+)', matched)
    if m:
        style.append("padding-left:{0}em".format(len(m.group(1))))
        matched = matched.replace(m.group(0), '')

    m = re.search(r'([)]+)', matched)
    if m:
        style.append("padding-right:{0}em".format(len(m.group(1))))
        matched = matched.replace(m.group(0), '')

    m = re.search(r'({0})'.format(halign_re_s), matched)
    if m:
        style.append("text-align:{0}".format(hAlign[m.group(1)]))

    m = re.search(r'^(.*)#(.*)$', aclass)
    if m:
        block_id = m.group(2)
        aclass = m.group(1)

    if element == 'col':
        pattern = r'(?:\\(\d+))?\s*(\d+)?'
        csp = re.match(pattern, matched)
        span, width = csp.groups()

    if style:
        # Previous splits that created style may have introduced extra
        # whitespace into the list elements.  Clean it up.
        style = [x.strip() for x in style]
        result['style'] = '{0};'.format("; ".join(style))
    if aclass:
        result['class'] = aclass
    if block_id and include_id:
        result['id'] = block_id
    if lang:
        result['lang'] = lang
    if colspan:
        result['colspan'] = colspan
    if rowspan:
        result['rowspan'] = rowspan
    if span:
        result['span'] = span
    if width:
        result['width'] = width
    return result
