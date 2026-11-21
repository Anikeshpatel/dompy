from pathlib import Path

import pytest

from dompy import (
    Comment,
    Document,
    DocumentFragment,
    DompyParser,
    Element,
    Node,
    SelectorError,
    Tags,
    Text,
)
from dompy.models import HTML_NAMESPACE, MATHML_NAMESPACE, SVG_NAMESPACE
from dompy.uitils import hasChildren


def test_legacy_entrypoints_and_nested_queries():
    markup = '<div><h3 color="blue" align="center">Abc</h3><h3>Xyz</h3></div>'
    root = DompyParser.parse(input=markup)
    assert isinstance(root, Element)
    assert root is root.ownerDocument.documentElement
    headings = root.getElementsByTag("H3")
    assert isinstance(headings, list)
    assert [element.innerHTML for element in headings] == ["Abc", "Xyz"]
    assert headings[0].attributes == {"color": "blue", "align": "center"}
    assert headings[0].content == "Abc"

    wrapped = Document(root)
    assert headings[0].ownerDocument is wrapped
    assert wrapped.root is root
    assert wrapped.getElementsByClass("missing") == []


@pytest.mark.parametrize(
    "markup", ["", "hello &amp; everyone", b"", memoryview(b"<p>ok")]
)
def test_implied_document_structure(markup):
    document = Document.fromString(markup)
    assert document.nodeName == "#document"
    assert document.ownerDocument is None
    assert document.root.tag == Tags.HTML
    assert document.root.parentNode is document
    assert document.head.parentElement is document.body.parentElement is document.root
    assert document.root.children == [document.head, document.body]
    assert document.doctype is None
    assert document.textContent is None
    assert document.compatMode == "BackCompat"


def test_mixed_nodes_and_relationships():
    document = Document.fromString(
        "<!doctype html><!--before--><div id=x>one\n  <b>two</b><!--keep -->"
        "<em>three &amp; four</em> tail</div><!--after-->"
    )
    box = document.getElementById("x")
    assert document.doctype.name == "html"
    assert document.doctype.nodeType == Node.DOCUMENT_TYPE_NODE
    assert document.doctype.nextSibling.data == "before"
    assert isinstance(box.firstChild, Text)
    assert box.firstChild.textContent == "one\n  "
    assert box.lastChild.data == " tail"
    assert isinstance(box.children[0].nextSibling, Comment)
    assert box.children[0].nextElementSibling is box.lastElementChild
    assert box.lastElementChild.previousElementSibling is box.firstElementChild
    assert box.childElementCount == 2
    assert box.textContent == "one\n  twothree & four tail"
    assert box.getRootNode() is document
    assert box.isConnected and document.contains(box)
    assert box.contains(box) and not box.contains(None)
    assert not box.firstChild.hasChildNodes()
    assert hasChildren(box)
    assert box.firstChild.parentElement is box
    assert document.nodeValue is box.nodeValue is None
    assert box.firstChild.nodeValue == box.firstChild.textContent
    assert (
        box.innerHTML == "one\n  <b>two</b><!--keep --><em>three &amp; four</em> tail"
    )


def test_malformed_nesting_and_attribute_recovery():
    document = Document.fromString(
        '<!doctype html><div DATA-value="a > b=c" class="a b" class=ignored>'
        "<p><b><i>first</b>second</i><p>third<br><img src=x><input disabled>"
        "<table>foster<tr><td>one<td>two</table></div>"
    )
    box = document.body.firstElementChild
    assert box.tagName == "DIV"
    assert box.getAttribute("DATA-VALUE") == "a > b=c"
    assert box.className == "a b"
    assert box.children[0].innerHTML == "<b><i>first</i></b><i>second</i>"
    assert box.children[1].innerHTML == 'third<br><img src="x"><input disabled="">'
    assert box.children[1].nextSibling.textContent == "foster"
    table = box.lastElementChild
    assert table.firstElementChild.tag == "tbody"
    assert [td.textContent for td in table.getElementsByTag("td")] == ["one", "two"]


def test_text_modes_and_serialization():
    doc = Document.fromString(
        '<title>  a\n\t b &amp; c </title><script>if (a < b) x = "<p>&amp;";</script>'
        "<pre>\n indent  </pre><textarea>\nx &lt; y</textarea><iframe><html>&amp;</iframe>"
        "<div title='&nbsp;&quot;&lt;&gt;&amp;'>&lt;&gt;&amp;&nbsp;</div>"
    )
    assert doc.title == "a b & c"
    assert doc.head.querySelector("script").innerHTML == 'if (a < b) x = "<p>&amp;";'
    assert doc.querySelector("pre").innerHTML == " indent  "
    assert doc.querySelector("textarea").textContent == "x < y"
    assert doc.querySelector("iframe").innerHTML == "<html>&amp;"
    assert doc.querySelector("div").outerHTML == (
        '<div title="&nbsp;&quot;&lt;&gt;&amp;">&lt;&gt;&amp;&nbsp;</div>'
    )
    assert doc.querySelector("script p, iframe html") is None


def test_noscript_modes_only_change_tree_building():
    markup = "<head><noscript><meta name=demo></noscript></head><body><noscript><p>fallback</noscript>"
    inert = Document.fromString(markup)
    assert inert.head.querySelector('meta[name="demo"]') is not None
    assert inert.querySelector("noscript p").textContent == "fallback"
    scripting = Document.fromString(markup, scripting=True)
    assert scripting.querySelector("meta, noscript p") is None
    assert scripting.body.firstElementChild.textContent == "<p>fallback"


def test_foreign_content_and_case():
    doc = Document.fromString(
        '<svg viewbox="0 0 5 5"><linearGradient ID=gradient/><use xlink:href="#gradient"></use>'
        "<foreignObject><div id=html></div></foreignObject></svg><math><mi>&alpha;</mi></math>"
    )
    svg, math = doc.body.children
    assert svg.namespaceURI == SVG_NAMESPACE
    assert svg.getAttribute("viewBox") == "0 0 5 5"
    assert svg.getAttribute("viewbox") is None
    assert svg.firstElementChild.tagName == "linearGradient"
    assert svg.getElementsByTag("lineargradient") == []
    assert svg.getElementsByTag("linearGradient") == [svg.firstElementChild]
    assert svg.querySelector("use").getAttribute("xlink:href") == "#gradient"
    assert doc.getElementById("html").namespaceURI == HTML_NAMESPACE
    assert math.namespaceURI == MATHML_NAMESPACE
    assert math.textContent == "α"


def test_template_content_is_a_separate_tree():
    doc = Document.fromString(
        "<template id=t><div id=hidden>x<template><b>nested</b></template></div></template>"
    )
    template = doc.getElementById("t")
    fragment = template.content
    assert isinstance(fragment, DocumentFragment)
    assert fragment is template.templateContent
    assert template.childNodes == []
    assert template.textContent == ""
    assert fragment.textContent == "x"
    assert not fragment.isConnected and fragment.parentNode is None
    assert fragment.ownerDocument is not doc
    assert fragment.ownerDocument.documentElement is None
    assert fragment.firstChild.ownerDocument is fragment.ownerDocument
    assert doc.getElementById("hidden") is None
    assert doc.querySelector("template div") is None
    assert fragment.getElementById("hidden") is fragment.querySelector("div")
    assert (
        fragment.querySelector("template").content.querySelector("b").textContent
        == "nested"
    )
    assert (
        template.innerHTML
        == '<div id="hidden">x<template><b>nested</b></template></div>'
    )
    template.innerHTML = "<tr><td>row"
    assert template.content is fragment
    assert template.innerHTML == "<tr><td>row</td></tr>"
    assert fragment.getElementById("hidden") is None


def test_query_order_scope_and_selector_errors():
    doc = Document.fromString(
        '<main class="scope"><div id="a:b" data-kind="Alpha" class="a b"></div>'
        '<div class="a"><span></span></div><aside class="b"></aside></main>'
    )
    main = doc.querySelector("main")
    first, second, aside = main.children
    assert doc.querySelector(":scope") is doc.root
    assert main.querySelector(":scope") is None
    assert main.querySelector("body main > div + div") is second
    assert main.querySelector(":scope > div:has(> span)") is second
    assert main.querySelector(r"#a\:b[data-kind='alpha' i]") is first
    assert main.querySelector(".a:nth-child(2)") is second
    assert main.querySelectorAll("aside, .a, div, .b") == [first, second, aside]
    assert second.matches("main > .a:not(.b)")
    assert second.closest("body") is doc.body
    assert second.closest(":scope") is second
    assert second.closest("missing") is None
    assert doc.getElementById("a:b") is first
    assert doc.getElementById("") is None
    for invalid in ("", "div,,p", "[", "::before", "@media"):
        with pytest.raises(SelectorError):
            doc.querySelectorAll(invalid)
    with pytest.raises(SelectorError):
        DocumentFragment().querySelector("div[")


def test_lookup_duplicate_ids_and_ascii_class_whitespace():
    doc = Document.fromString(
        '<p id=dup class="a  a\tb\u00a0c"><p id=dup class="a b c">'
    )
    first, second = doc.body.children
    assert doc.getElementById("dup") is first
    assert doc.getElementsByClass("a b") == [second]
    assert doc.getElementsByClass("a b\u00a0c") == [first]
    assert doc.getElementsByClassName("  \t") == []
    assert list(first.classList) == ["a", "b\u00a0c"]


def test_live_collections_and_static_queries():
    doc = Document.fromString("<ul><li>first</li></ul>")
    ul = doc.querySelector("ul")
    child_nodes = ul.childNodes
    children = ul.children
    tags = doc.getElementsByTagName("li")
    classes = ul.getElementsByClassName("item")
    snapshot = ul.querySelectorAll("li")
    legacy = ul.getElementsByTag("li")
    li = doc.createElement("LI")
    li.className = "item"
    ul.appendChild(li)
    assert len(child_nodes) == len(children) == len(tags) == 2
    assert [*tags] == [ul.firstChild, li]
    assert classes[0] is li and tags[-1] is li
    assert tags.item(1) is li and tags.item(2) is None and tags.item(-1) is None
    assert tags[:] == [ul.firstChild, li]
    assert len(snapshot) == len(legacy) == 1
    li.classList.remove("item")
    assert not classes
    li.remove()
    assert len(child_nodes) == 1


def test_attributes_and_live_class_list():
    node = Element("div")
    assert node.id == ""
    assert not node.hasAttribute("id")
    node.setAttribute("ID", 123)
    assert node.id == "123"
    assert node.attributes == {"id": "123"}
    node.id = "new"
    assert node.getAttribute("ID") == "new"
    node.removeAttribute("ID")
    assert node.getAttribute("id") is None
    with pytest.raises(ValueError):
        node.setAttribute("bad name", "x")

    classes = node.classList
    assert classes is node.classList
    classes.remove("missing")
    assert not node.hasAttribute("class")
    node.className = "blue  blue\tgreen"
    assert list(classes) == ["blue", "green"]
    assert classes.contains("green")
    assert str(classes) == node.className
    classes.add("yellow", "blue")
    assert classes.value == "blue green yellow"
    assert classes.replace("green", "blue")
    assert not classes.replace("missing", "blue")
    assert classes.toggle("blue") is False
    assert classes.toggle("blue", False) is False
    assert classes.toggle("red", True) is True
    assert classes.toggle("red") is False
    with pytest.raises(ValueError):
        classes.add("valid", "two words")
    with pytest.raises(TypeError):
        classes.toggle(None)
    assert classes.value == "yellow"


def test_fragment_context_and_mutations():
    doc = Document.fromString("<table></table><div id=destination></div>")
    table = doc.querySelector("table")
    fragment = DompyParser.parseFragment("<tr><td>one<td>two", context=table)
    assert fragment.ownerDocument is doc
    assert fragment.firstChild.tag == "tbody"
    table.appendChild(fragment)
    assert fragment.childNodes == []
    assert table.innerHTML == "<tbody><tr><td>one</td><td>two</td></tr></tbody>"

    target = doc.getElementById("destination")
    target.innerHTML = "alpha<!-- comment --><b>beta</b>gamma"
    saved = target.firstElementChild
    assert target.textContent == "alphabetagamma"
    target.textContent = "<label>&"
    assert saved.parentNode is None and saved.ownerDocument is doc
    assert target.innerHTML == "&lt;label&gt;&amp;"
    target.innerHTML = None
    assert not target.hasChildNodes()


@pytest.mark.parametrize(
    ("before", "selector", "source", "output"),
    [
        ("<textarea></textarea>", "textarea", "\n&lt;a&gt;", "\n&lt;a&gt;"),
        ("<form><div></div></form>", "div", "<form><input></form>", "<input>"),
        (
            "<form><div></div></form>",
            "div",
            "</form><form><input></form>",
            "<form><input></form>",
        ),
        (
            "<template></template>",
            "template",
            "</template><tr><td>x",
            "<tr><td>x</td></tr>",
        ),
        (
            "<svg></svg>",
            "svg",
            "<circle/><foreignObject><p>x</p></foreignObject>",
            "<circle></circle><foreignObject><p>x</p></foreignObject>",
        ),
    ],
)
def test_inner_html_contexts(before, selector, source, output):
    target = Document.fromString(before).querySelector(selector)
    target.innerHTML = source
    assert target.innerHTML == output


def test_reparenting_and_replacing_preserve_identity():
    doc = Document.fromString("<div><b>one</b><em>two</em><i>three</i></div>")
    box = doc.body.firstElementChild
    bold, emphasis, italic = box.children
    assert box.insertBefore(italic, bold) is italic
    assert box.insertBefore(italic, italic) is italic
    assert box.children == [italic, bold, emphasis]
    assert box.replaceChild(emphasis, italic) is italic
    assert box.children == [emphasis, bold]
    assert italic.parentNode is None
    fragment = doc.createDocumentFragment()
    fragment.appendChild(italic)
    fragment.appendChild(doc.createComment("note"))
    assert box.replaceChild(fragment, emphasis) is emphasis
    assert box.childNodes[0] is italic
    assert box.childNodes[1].data == "note"
    assert emphasis.parentNode is None
    assert fragment.childNodes == []
    assert box.removeChild(bold) is bold
    assert bold.parentNode is None
    with pytest.raises(ValueError):
        box.removeChild(bold)
    with pytest.raises(TypeError):
        box.removeChild(None)


def test_invalid_document_mutations_leave_trees_intact():
    doc = Document.fromString("<!doctype html><p>content")
    p = doc.querySelector("p")
    fragment = doc.createDocumentFragment()
    element = Document.fromString("<b>x").body.firstElementChild
    fragment.appendChild(element)
    fragment.appendChild(doc.createElement("span"))
    original = str(doc)

    with pytest.raises(ValueError):
        doc.replaceChild(fragment, doc.root)
    assert fragment.children[0] is element
    with pytest.raises(ValueError):
        doc.insertBefore(doc.root, doc.doctype)
    with pytest.raises(ValueError):
        doc.appendChild(Text("forbidden"))
    with pytest.raises(ValueError):
        p.appendChild(doc.root)
    with pytest.raises(ValueError):
        p.appendChild(doc.doctype)
    with pytest.raises(ValueError):
        p.appendChild(doc)
    with pytest.raises(ValueError):
        p.insertBefore(element, doc.head)
    with pytest.raises(TypeError):
        p.appendChild("invalid")
    with pytest.raises(TypeError):
        p.replaceChild(element, None)
    assert str(doc) == original

    template = doc.createElement("template")
    with pytest.raises(ValueError):
        template.content.appendChild(template)
    with pytest.raises(ValueError):
        template.content.appendChild(template.content)


def test_cloning_and_adoption_across_documents():
    original = Document.fromString(
        "<div id=x><template><b>inert</b></template>hello</div>"
    )
    div = original.getElementById("x")
    copy = div.cloneNode(True)
    shallow = div.cloneNode()
    assert copy.outerHTML == div.outerHTML
    assert copy.children[0].content is not div.children[0].content
    assert shallow.outerHTML == '<div id="x"></div>'
    assert copy.ownerDocument is original and copy.parentNode is None
    cloned_doc = original.cloneNode(True)
    assert str(cloned_doc) == str(original)
    template_copy = cloned_doc.querySelector("template").content
    assert (
        template_copy.ownerDocument
        is not original.querySelector("template").content.ownerDocument
    )
    assert template_copy.firstChild.ownerDocument is template_copy.ownerDocument
    destination = Document.fromString("")
    destination.body.appendChild(div)
    assert original.getElementById("x") is None
    assert destination.getElementById("x") is div
    assert div.lastChild.ownerDocument is destination
    assert (
        div.children[0].content.ownerDocument
        is destination.createElement("template").content.ownerDocument
    )
    assert (
        div.children[0].content.firstChild.ownerDocument
        is div.children[0].content.ownerDocument
    )
    copy.id = "edited"
    assert div.id == "x"


def test_deep_and_wide_documents():
    depth = 2000
    wide = 500
    doc = Document.fromString(
        "<div>" * depth
        + "<span>deep</span>"
        + "</div>" * depth
        + "<p class=item></p>" * wide
    )
    assert len(doc.getElementsByTagName("div")) == depth
    assert doc.querySelector("div span").textContent == "deep"
    assert str(doc.cloneNode(True)) == str(doc)
    assert len(doc.querySelectorAll("p.item")) == wide


def test_repository_fixture():
    fixture = Path(__file__).resolve().parents[1] / "index.html"
    doc = Document.fromFile(fixture)
    assert doc.title == "Natours | Exciting tours for adventurous people"
    assert len(doc.querySelectorAll("section")) >= 5
