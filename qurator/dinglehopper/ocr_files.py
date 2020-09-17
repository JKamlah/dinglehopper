from __future__ import division, print_function

from warnings import warn

from lxml import etree as ET
import sys

from lxml.etree import XMLSyntaxError


def alto_namespace(tree):
    """Return the ALTO namespace used in the given ElementTree.

    This relies on the assumption that, in any given ALTO file, the root element has the local name "alto". We do not
    check if the files uses any valid ALTO namespace.
    """
    root_name = ET.QName(tree.getroot().tag)
    if root_name.localname == 'alto':
        return root_name.namespace
    else:
        raise ValueError('Not an ALTO tree')


def alto_text(tree):
    """Extract text from the given ALTO ElementTree."""

    nsmap = {'alto': alto_namespace(tree)}

    lines = (
        ' '.join(string.attrib.get('CONTENT') for string in line.iterfind('alto:String', namespaces=nsmap))
        for line in tree.iterfind('.//alto:TextLine', namespaces=nsmap))
    text_ = '\n'.join(lines)

    return text_


def page_namespace(tree):
    """Return the PAGE content namespace used in the given ElementTree.

    This relies on the assumption that, in any given PAGE content file, the root element has the local name "PcGts". We
    do not check if the files uses any valid PAGE namespace.
    """
    root_name = ET.QName(tree.getroot().tag)
    if root_name.localname == 'PcGts':
        return root_name.namespace
    else:
        raise ValueError('Not a PAGE tree')


def page_text(tree, level="region", index="0"):
    """Extract text from the given PAGE content ElementTree."""

    nsmap = {'page': page_namespace(tree)}

    def region_text(region, index="0"):
        try:
            reg = region.find('./page:TextEquiv/page:Unicode', namespaces=nsmap)
            if reg is not None and reg.getparent().attrib.get('index','-1') in ['-1', index]:
                return region.find('./page:TextEquiv/page:Unicode', namespaces=nsmap).text
            else:
                return None
        except AttributeError:
            return None

    def line_text(region, index="0"):
        try:
            return "\n".join([line.text for line in (region.findall('./page:TextLine/page:TextEquiv/page:Unicode', namespaces=nsmap))
                              if line is not None and line.getparent().attrib.get('index','-1') in ['-1', index]])
        except AttributeError:
            return None

    def word_text(region, index="0"):
        try:
            text = []
            textlines = []
            lines = region.findall('./page:TextLine/', namespaces=nsmap)
            for line in lines:
                words = line.findall('./page:TextEquiv/page:Unicode', namespaces=nsmap)
                if words:
                    for word in words:
                        if word.getparent().attrib.get('index','-1') in ['-1', index]:
                            text.append(word.text)
                elif text != []:
                    textlines.append(" ".join(text))
                    text = []
            return "\n".join(textlines)
        except AttributeError:
            return None

    region_texts = []
    reading_order = tree.find('.//page:ReadingOrder', namespaces=nsmap)
    if reading_order is not None:
        for group in reading_order.iterfind('./*', namespaces=nsmap):
            if ET.QName(group.tag).localname == 'OrderedGroup':
                region_ref_indexeds = group.findall('./page:RegionRefIndexed', namespaces=nsmap)
                for region_ref_indexed in sorted(region_ref_indexeds, key=lambda r: int(r.attrib['index'])):
                    region_id = region_ref_indexed.attrib['regionRef']
                    region = tree.find('.//page:TextRegion[@id="%s"]' % region_id, namespaces=nsmap)
                    if region is not None and level == "region":
                        region_texts.append(region_text(region, index))
                    elif region is not None and level == "line":
                        region_texts.append(line_text(region, index))
                    elif region is not None and level == "word":
                        region_texts.append(word_text(region, index))
                    else:
                        warn('Not a TextRegion: "%s"' % region_id)
            else:
                raise NotImplementedError
    else:
        for region in tree.iterfind('.//page:TextRegion', namespaces=nsmap):
            if region is not None and level == "region":
                region_texts.append(region_text(region, index))
            elif region is not None and level == "line":
                region_texts.append(line_text(region, index))
            elif region is not None and level == "word":
                region_texts.append(word_text(region, index))

    # XXX Does a file have to have regions etc.? region vs lines etc.
    # Filter empty region texts
    region_texts = (t for t in region_texts if t)

    text_ = '\n'.join(region_texts)

    return text_


def text(filename, level="region", index="0"):
    """Read the text from the given file.

    Supports PAGE, ALTO and falls back to plain text.
    """

    try:
        tree = ET.parse(filename)
    except XMLSyntaxError:
        with open(filename, 'r') as f:
            return f.read()
    try:
        return page_text(tree, level=level, index=index)
    except ValueError:
        return alto_text(tree)


if __name__ == '__main__':
    print(text(sys.argv[1]))
