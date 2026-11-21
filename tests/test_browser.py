"""Optional parity tests against a real browser's inert HTML DOM."""

import os

import pytest

from dompy import Document, Element

CASES = [
    "",
    "\ufeff<html><head><title>Byte order mark</title></head><body>",
    "plain &amp; text\r\nwith whitespace",
    "<?demo begin?><p>Hello<?empty?><?xml version=1?>",
    "<!doctype html><!-- A --><HTML LANG=en><title> A &amp; B </title><p>hi<!-- B -->there</p><!-- C -->",
    "<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' 'about:legacy-compat'>"
    "<UL><LI>a<li>b</ul><p>before<div>inside</div>after",
    "<!doctype html><b><i>one</b>two</i> end <a href=x><a href=y>nested",
    "<!doctype html><table>foster<tr><td>one<td>two</table><select><option>a<option>b</select>",
    "<!doctype html><style>body > p { content: '&amp;' }</style>"
    "<script>if (a < b && c > d) x = '<p>';</script>"
    "<textarea>\nline\r\n &lt;x&gt;</textarea><pre>\n  indented</pre>",
    "<!doctype html><noscript><meta name=x></noscript><body><noscript><p>Fallback</noscript>",
    "<!doctype html><svg viewBox='0 0 1 1'><use xlink:href='#x'/>"
    "<foreignObject><p data-hint='a > b &amp; &lt; &quot;'>&nbsp;</p></foreignObject>"
    "<linearGradient id='x'/></svg><math><mtext><b>math integration</b></mtext></math>",
    "<!doctype html><template><tr><td>x<template><b>nested</b></template></template><p>live",
    "<!doctype html><title>&lt;title&gt;</title><!-- a --> <input DISABLED data-x='a=b > c' data-x=no>"
    "<br><iframe><p>raw text &amp;</iframe><custom-x/><p>not a void element",
    "<!doctype html><p>&notit; &notin; &#x80; &#0; &#x1f33b; &acE;<p title='&notit; &notin;'>",
    "<!doctype html><frameset cols='*'><frame src='about:blank'></frameset>",
    "<!doctype html><script><!-- <script> double escaped </script> --></script><p>after",
]

TREE_SCRIPT = """
function tree(node) {
    const result = {type: node.nodeType, name: node.nodeName, text: node.nodeValue};
    if (node.nodeType === 1) {
        result.ns = node.namespaceURI;
        result.attrs = Array.from(node.attributes, attr => [attr.name, attr.value]);
        if (node.localName === "template" && node.content) result.content = tree(node.content);
    }
    if (node.nodeType === 10) {
        result.publicId = node.publicId;
        result.systemId = node.systemId;
    }
    result.children = Array.from(node.childNodes, tree);
    return result;
}
"""


def tree(node):
    result = {
        "type": node.nodeType,
        "name": node.nodeName,
        "text": getattr(node, "nodeValue", None),
        "children": [tree(child) for child in node.childNodes],
    }
    if isinstance(node, Element):
        result["ns"] = node.namespaceURI
        result["attrs"] = [list(pair) for pair in node.attributes.items()]
        if node.templateContent is not None:
            result["content"] = tree(node.templateContent)
    if node.nodeType == node.DOCUMENT_TYPE_NODE:
        result.update(publicId=node.publicId, systemId=node.systemId)
    return result


@pytest.fixture(scope="module")
def page():
    if not os.environ.get("DOMPY_BROWSER"):
        pytest.skip("Set DOMPY_BROWSER=chromium or chrome to run browser parity tests")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ["DOMPY_BROWSER"])
        context = browser.new_context(offline=True)
        yield context.new_page()
        browser.close()


@pytest.mark.parametrize("markup", CASES)
def test_document_parity(page, markup):
    expected = page.evaluate(
        "(markup) => {"
        + TREE_SCRIPT
        + """
        const doc = new DOMParser().parseFromString(markup, 'text/html');
        return [tree(doc), doc.documentElement.outerHTML, doc.title, doc.compatMode];
        }""",
        markup,
    )
    doc = Document.fromString(markup)
    assert [
        tree(doc),
        doc.documentElement.outerHTML,
        doc.title,
        doc.compatMode,
    ] == expected


@pytest.mark.parametrize(
    ("before", "tag", "markup"),
    [
        ("<table></table>", "table", "<tr><td>1<td>2"),
        ("<select></select>", "select", "<optgroup label=x><option>A<option>B"),
        ("<textarea></textarea>", "textarea", "\nhello &amp; <b>text</b>"),
        ("<script></script>", "script", "<b>x</b> &amp;"),
        ("<template></template>", "template", "<tr><td>x<!--w-->"),
        ("<svg></svg>", "svg", "<circle/><foreignObject><p>x</p></foreignObject>"),
        ("<div></div>", "div", "<p>mixed <b>text</b><!-- hi --> "),
        ("", "html", "<title>x</title><body class=ready><b>markup</b>"),
        (
            "",
            "html",
            "<!doctype html><head></head><body><p><table><tr><td>quirks</table>",
        ),
        ("<form><div></div></form>", "div", "<form><input></form><p>after"),
        (
            '<math><annotation-xml encoding="text/html"></annotation-xml></math>',
            "annotation-xml",
            "<svg></svg><input><p>HTML integration</p>",
        ),
    ],
)
def test_inner_html_parity(page, before, tag, markup):
    expected = page.evaluate(
        "([before, tag, markup]) => {"
        + TREE_SCRIPT
        + """
        const doc = new DOMParser().parseFromString(before, 'text/html');
        const element = doc.querySelector(tag);
        element.innerHTML = markup;
        return [tree(element), element.innerHTML];
        }""",
        [before, tag, markup],
    )
    element = Document.fromString(before).querySelector(tag)
    element.innerHTML = markup
    assert [tree(element), element.innerHTML] == expected


@pytest.mark.parametrize(
    "selector",
    [
        ":scope > .item",
        "main > .item + .item",
        "body main span",
        "#one, .item, [data-kind=blue]",
        "[data-kind='BLUE' i]",
        "div:has(> span)",
        "div:nth-child(2 of .item)",
        "div:not(:has(span)):is(.item, .other)",
        "#a\\:b",
        ":root",
        "linearGradient",
        "lineargradient",
        "DiV",
    ],
)
def test_selectors_parity(page, selector):
    markup = (
        "<!doctype html><main><div class=item id=one data-kind=Blue><span id=a:b></span></div>"
        "<div class=item id=two></div><p id=three></p><svg><linearGradient id=svg /></svg>"
        "<template><div class=item id=hidden></div></template></main>"
    )
    expected = page.evaluate(
        """([markup, selector]) => {
            const doc = new DOMParser().parseFromString(markup, 'text/html');
            return [doc, doc.querySelector('main')].map(
                root => [...root.querySelectorAll(selector)].map(el => el.id)
            );
        }""",
        [markup, selector],
    )
    doc = Document.fromString(markup)
    assert [
        [el.id for el in root.querySelectorAll(selector)]
        for root in (doc, doc.querySelector("main"))
    ] == expected


def test_quirks_and_detached_fragment_selectors_parity(page):
    markup = "<p id=FOO class=A><template><div><b></b></div></template>"
    expected = page.evaluate(
        """(markup) => {
          const doc = new DOMParser().parseFromString(markup, 'text/html');
          const frag = doc.querySelector('template').content;
          return [doc.querySelectorAll('#foo.a').length, doc.getElementsByClassName('a').length,
                  doc.querySelectorAll('[id=foo]').length,
                  frag.querySelectorAll(':scope > b, :root').length];
        }""",
        markup,
    )
    doc = Document.fromString(markup)
    fragment = doc.querySelector("template").content
    assert [
        len(doc.querySelectorAll("#foo.a")),
        len(doc.getElementsByClassName("a")),
        len(doc.querySelectorAll("[id=foo]")),
        len(fragment.querySelectorAll(":scope > b, :root")),
    ] == expected


def test_mutation_and_template_owner_parity(page):
    expected = page.evaluate(
        "() => {"
        + TREE_SCRIPT
        + """
        const first = new DOMParser().parseFromString('<div><template><b>x</b></template></div>', 'text/html');
        const second = new DOMParser().parseFromString('', 'text/html');
        const div = first.querySelector('div');
        const template = div.querySelector('template');
        const live = second.getElementsByTagName('p');
        second.body.appendChild(div);
        const fragment = first.createDocumentFragment();
        fragment.appendChild(first.createComment('moved'));
        const paragraph = first.createElement('p');
        paragraph.textContent = 'edited & escaped';
        fragment.appendChild(paragraph);
        div.insertBefore(fragment, template);
        const child = template.content.firstChild;
        div.replaceChild(child, paragraph);
        return [
            tree(second.body), live.length,
            div.ownerDocument === second, child.ownerDocument === second,
            template.content.ownerDocument === second.createElement('template').content.ownerDocument,
            fragment.ownerDocument === first, paragraph.parentNode === null,
        ];
        }"""
    )
    first = Document.fromString("<div><template><b>x</b></template></div>")
    second = Document.fromString("")
    div = first.querySelector("div")
    template = div.querySelector("template")
    live = second.getElementsByTagName("p")
    second.body.appendChild(div)
    fragment = first.createDocumentFragment()
    fragment.appendChild(first.createComment("moved"))
    paragraph = first.createElement("p")
    paragraph.textContent = "edited & escaped"
    fragment.appendChild(paragraph)
    div.insertBefore(fragment, template)
    child = template.content.firstChild
    div.replaceChild(child, paragraph)
    assert [
        tree(second.body),
        len(live),
        div.ownerDocument is second,
        child.ownerDocument is second,
        template.content.ownerDocument
        is second.createElement("template").content.ownerDocument,
        fragment.ownerDocument is first,
        paragraph.parentNode is None,
    ] == expected
