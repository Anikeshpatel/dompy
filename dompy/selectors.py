"""Adapt the DOM tree for Soup Sieve's CSS selector engine."""

from bs4 import BeautifulSoup
from bs4 import Comment as SoupComment
from bs4 import ProcessingInstruction as SoupInstruction
from soupsieve import SelectorSyntaxError as SelectorError
from soupsieve import compile as compile_selector
from soupsieve.css_match import CSSMatch

from .models import Comment, Element, Node, ProcessingInstruction, Text, ascii_lower


class _DOMMatcher(CSSMatch):
    def __init__(self, compiled, tag, scope, root):
        super().__init__(compiled.selectors, tag, compiled.namespaces, compiled.flags)
        if root.nodeType != Node.DOCUMENT_NODE:
            self.root = None
        if scope.nodeType == Node.DOCUMENT_FRAGMENT_NODE:
            self.scope = None
        document = root if root.nodeType == Node.DOCUMENT_NODE else root.ownerDocument
        self.quirks = document is not None and document.compatMode == "BackCompat"

    def match_id(self, el, ids):
        if self.quirks:
            value = ascii_lower(self.get_attribute_by_name(el, "id", ""))
            return all(ascii_lower(identifier) == value for identifier in ids)
        return super().match_id(el, ids)

    def match_classes(self, el, classes):
        if self.quirks:
            values = {ascii_lower(value) for value in self.get_classes(el)}
            return all(ascii_lower(token) in values for token in classes)
        return super().match_classes(el, classes)


def _projection(scope):
    # Match against the whole containing tree. The search scope limits which
    # nodes are returned, while combinators can still inspect its ancestors.
    soup = BeautifulSoup("", "html.parser")
    root = scope.getRootNode()
    element_by_tag = {}
    scope_tag = soup
    if isinstance(root, Element):
        stack = [(root, soup)]
    else:
        stack = [(node, soup) for node in reversed(root._children)]

    while stack:
        node, parent = stack.pop()
        if isinstance(node, Element):
            tag = soup.new_tag(
                node.localName, namespace=node.namespaceURI, attrs=node.attributes
            )
            parent.append(tag)
            element_by_tag[id(tag)] = node
            if node is scope:
                scope_tag = tag
            stack.extend((child, tag) for child in reversed(node._children))
        elif isinstance(node, Text):
            parent.append(soup.new_string(node.data))
        elif isinstance(node, Comment):
            parent.append(soup.new_string(node.data, SoupComment))
        elif isinstance(node, ProcessingInstruction):
            parent.append(soup.new_string(node.data, SoupInstruction))
    return scope_tag, element_by_tag, root


def _compile(selector):
    try:
        return compile_selector(selector)
    except NotImplementedError as error:
        raise SelectorError(str(error)) from error


def _matcher(scope, selector):
    compiled = _compile(selector)
    tag, elements, root = _projection(scope)
    return _DOMMatcher(compiled, tag, scope, root), elements


def select(scope, selector, *, first=False):
    matcher, elements = _matcher(scope, selector)
    if first:
        match = next(matcher.select(limit=1), None)
        return None if match is None else elements[id(match)]
    return [elements[id(match)] for match in matcher.select()]


def match(element, selector):
    matcher, _ = _matcher(element, selector)
    return matcher.match(matcher.tag)


def closest(element, selector):
    matcher, elements = _matcher(element, selector)
    match = matcher.closest()
    return None if match is None else elements[id(match)]


__all__ = ["SelectorError"]
