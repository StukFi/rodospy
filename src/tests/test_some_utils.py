import pytest
import os
from xml.dom.minidom import parse, getDOMImplementation, parseString

# pytests is newer the pyunit
# https://docs.pytest.org/en/latest/getting-started.html

# RUNNING TEST:
#  pytest tests/test_some_utils.py
# seeing print statements in terminal
#  pytest --capture=no tests/test_some_utils.py

# create a fixture as a function
# https://docs.pytest.org/en/latest/fixture.html#fixtures
@pytest.fixture
def filepath():
    return './tests/data/ground.sld'

@pytest.fixture
def outpath():
    return '/var/www/html/sld/ground4.sld'

@pytest.fixture
def dom(filepath):
    return parse(filepath)

# pass the fixture as argument
def test_open_sld_file(filepath):
    assert os.path.isfile(filepath)
    assert os.path.exists(filepath)
    with open(filepath, 'r') as f:
        assert True
        return
    assert False

def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

#@pytest.mark.skip()
def test_show_literals(dom, outpath):
    cssparam_elements = dom.getElementsByTagName('CssParameter')
    # remove Literal Elements and set value from it to CssParameter
    # https://mapserver.org/development/rfc/ms-rfc-124.html Currently, MapServer only supports raw constants in <CssParameter> or <SvgParameter> tags, e.g.:
    for css in cssparam_elements:
        literal_elements = css.getElementsByTagName('Literal')
        for lit in literal_elements:
            value = getText(lit.childNodes)
            css.removeChild(lit)
            v = dom.createTextNode(value)
            css.appendChild(v)

    impl = getDOMImplementation()
    newdom = impl.createDocument(None, "StyledLayerDescriptor", None)
    #styledLayerDescriptor = dom.createElementNode('StyledLayerDescriptor')
    namedLayer = newdom.createElement('NamedLayer')
    name = newdom.createElement('Name')
    n = newdom.createTextNode('ground')  # <== YOU REALLY HAVE TO GIVE IT THE SAME NAME AS YOUR LAYER!
    newdom.childNodes[0].appendChild(namedLayer).appendChild(name).appendChild(n)
    namedLayer.appendChild(dom.childNodes[0])

    #print(dom.toprettyxml(indent='  '))
    print(newdom.toprettyxml(indent='  '))
    f = open(outpath, 'w')
    newdom.writexml(f, indent='  ', addindent='  ', newl='\n')
    f.close()
    assert True

@pytest.mark.skip()
def test_print_sld_xml(dom):
    print(dom.toprettyxml(indent='  '))
    assert True
