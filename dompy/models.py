"""Nodes and tree operations for an HTML document."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import cached_property
from typing import Generic, TypeVar

HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
MATHML_NAMESPACE = "http://www.w3.org/1998/Math/MathML"
HTML_WHITESPACE = " \t\n\r\f"
_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_TOKEN_PATTERN = re.compile(r"[^ \t\n\r\f]+")
_T = TypeVar("_T")


def ascii_lower(value: str) -> str:
    return value.translate(_ASCII_LOWER)


def tokens(value: str) -> list[str]:
    return list(dict.fromkeys(_TOKEN_PATTERN.findall(value)))


class _LiveCollection(Sequence[_T], Generic[_T]):
    """Resolve a collection against the tree whenever it is read."""

    def __init__(self, members: Callable[[], Iterable[_T]]) -> None:
        self._members = members

    def __iter__(self) -> Iterator[_T]:
        return iter(self._members())

    def __len__(self) -> int:
        return sum(1 for _ in self._members())

    def __getitem__(self, index):
        return list(self._members())[index]

    def __eq__(self, other):
        if not isinstance(other, (list, tuple, _LiveCollection)):
            return NotImplemented
        return list(self) == list(other)

    def item(self, index: int) -> _T | None:
        if index < 0:
            return None
        try:
            return self[index]
        except IndexError:
            return None


class Node:
    ELEMENT_NODE = 1
    TEXT_NODE = 3
    PROCESSING_INSTRUCTION_NODE = 7
    COMMENT_NODE = 8
    DOCUMENT_NODE = 9
    DOCUMENT_TYPE_NODE = 10
    DOCUMENT_FRAGMENT_NODE = 11

    def __init__(self) -> None:
        self._parent: ParentNode | None = None
        self._children: list[Node] = []
        self._document = None

    @property
    def ownerDocument(self):
        return self._document

    @property
    def parentNode(self) -> ParentNode | None:
        return self._parent

    @property
    def parentElement(self) -> Element | None:
        return self._parent if isinstance(self._parent, Element) else None

    @cached_property
    def childNodes(self) -> _LiveCollection[Node]:
        return _LiveCollection(lambda: self._children)

    @property
    def firstChild(self) -> Node | None:
        return self._children[0] if self._children else None

    @property
    def lastChild(self) -> Node | None:
        return self._children[-1] if self._children else None

    @property
    def previousSibling(self) -> Node | None:
        if self._parent is None:
            return None
        siblings = self._parent._children
        index = siblings.index(self)
        return siblings[index - 1] if index else None

    @property
    def nextSibling(self) -> Node | None:
        if self._parent is None:
            return None
        siblings = self._parent._children
        index = siblings.index(self) + 1
        return siblings[index] if index < len(siblings) else None

    @property
    def isConnected(self) -> bool:
        return self.getRootNode().nodeType == self.DOCUMENT_NODE

    def getRootNode(self) -> Node:
        node = self
        while node._parent is not None:
            node = node._parent
        return node

    def contains(self, other: Node | None) -> bool:
        while other is not None:
            if other is self:
                return True
            other = other._parent
        return False

    def hasChildNodes(self) -> bool:
        return bool(self._children)

    def _descendants(self) -> Iterator[Node]:
        stack = list(reversed(self._children))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node._children))

    @property
    def textContent(self) -> str | None:
        return None

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        pass

    nodeValue = textContent

    def remove(self) -> None:
        if self._parent is not None:
            self._parent.removeChild(self)

    def _set_document(self, document) -> None:
        stack = [(self, document)]
        while stack:
            node, owner = stack.pop()
            node._document = owner
            stack.extend((child, owner) for child in node._children)
            if isinstance(node, Element) and node.templateContent is not None:
                stack.append(
                    (node.templateContent, owner._template_owner() if owner else None)
                )

    def _copy(self) -> Node:
        return type(self)()

    def cloneNode(self, deep: bool = False) -> Node:
        clone = self._copy()
        clone._document = self.ownerDocument
        stack = [(self, clone)]
        while stack:
            source, target = stack.pop()
            document = (
                target
                if target.nodeType == self.DOCUMENT_NODE
                else target.ownerDocument
            )
            if isinstance(source, Element) and source.templateContent is not None:
                target.templateContent._document = (
                    document._template_owner() if document else None
                )
                if deep:
                    stack.append((source.templateContent, target.templateContent))
            if deep:
                for child in source._children:
                    child_copy = child._copy()
                    child_copy._document = document
                    target._append(child_copy)
                    stack.append((child, child_copy))
        return clone

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.nodeName!r}>"


class CharacterData(Node):
    def __init__(self, data: str = "") -> None:
        super().__init__()
        self.data = data

    @property
    def textContent(self) -> str:
        return self.data

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        self.data = "" if value is None else value

    nodeValue = textContent

    def _copy(self) -> CharacterData:
        return type(self)(self.data)


class Text(CharacterData):
    nodeName = "#text"
    nodeType = Node.TEXT_NODE


class Comment(CharacterData):
    nodeName = "#comment"
    nodeType = Node.COMMENT_NODE


class ProcessingInstruction(CharacterData):
    nodeType = Node.PROCESSING_INSTRUCTION_NODE

    def __init__(self, target: str, data: str = "") -> None:
        super().__init__(data)
        self.target = self.nodeName = target

    def _copy(self) -> ProcessingInstruction:
        return ProcessingInstruction(self.target, self.data)


class DocumentType(Node):
    nodeType = Node.DOCUMENT_TYPE_NODE

    def __init__(self, name: str, public_id: str = "", system_id: str = "") -> None:
        super().__init__()
        self.name = self.nodeName = name
        self.publicId = public_id
        self.systemId = system_id

    def _copy(self) -> DocumentType:
        return DocumentType(self.name, self.publicId, self.systemId)


class ParentNode(Node):
    @cached_property
    def children(self) -> _LiveCollection[Element]:
        return _LiveCollection(
            lambda: (node for node in self._children if isinstance(node, Element))
        )

    @property
    def childElementCount(self) -> int:
        return len(self.children)

    @property
    def firstElementChild(self) -> Element | None:
        return next(
            (node for node in self._children if isinstance(node, Element)), None
        )

    @property
    def lastElementChild(self) -> Element | None:
        return next(
            (node for node in reversed(self._children) if isinstance(node, Element)),
            None,
        )

    @property
    def textContent(self) -> str | None:
        return "".join(
            node.data for node in self._descendants() if isinstance(node, Text)
        )

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        self._replace_children([Text(value)] if value else [])

    def _elements(self) -> Iterator[Element]:
        return (node for node in self._descendants() if isinstance(node, Element))

    def querySelector(self, selector: str) -> Element | None:
        from .selectors import select

        return select(self, selector, first=True)

    def querySelectorAll(self, selector: str) -> list[Element]:
        from .selectors import select

        return select(self, selector)

    def _append(self, node: Node) -> None:
        """Attach a fresh node while parsing or cloning."""
        self._children.append(node)
        node._parent = self

    def _replace_children(self, nodes: list[Node]) -> None:
        for child in self._children:
            child._parent = None
        self._children.clear()
        self._children.extend(nodes)
        for child in nodes:
            child._parent = self
            child._set_document(self.ownerDocument)

    def _insert(
        self, node: Node, reference: Node | None, *, replacing: bool = False
    ) -> None:
        if not isinstance(node, Node):
            raise TypeError("Expected a Node")
        if reference is not None and reference._parent is not self:
            raise ValueError("Reference node is not a child of this parent")
        if node is reference:
            return

        # The host of a template fragment also counts as an ancestor for insertion.
        ancestor = self
        while ancestor is not None:
            if ancestor is node:
                raise ValueError("Cannot insert a node into itself or its descendants")
            ancestor = (
                ancestor._host
                if isinstance(ancestor, DocumentFragment) and ancestor._host
                else ancestor._parent
            )

        incoming = (
            node._children.copy() if isinstance(node, DocumentFragment) else [node]
        )
        if any(child.nodeType == self.DOCUMENT_NODE for child in incoming):
            raise ValueError("Cannot insert a document into a node")
        if self.nodeType == self.DOCUMENT_NODE:
            children = [child for child in self._children if child is not node]
            index = len(children) if reference is None else children.index(reference)
            children[index : index + int(replacing)] = incoming
            self._validate_children(children)
        elif any(child.nodeType == self.DOCUMENT_TYPE_NODE for child in incoming):
            raise ValueError("A doctype can only be a child of a document")

        document = self if self.nodeType == self.DOCUMENT_NODE else self.ownerDocument
        for child in incoming:
            child.remove()
        index = (
            len(self._children)
            if reference is None
            else self._children.index(reference)
        )
        if replacing:
            reference._parent = None
        self._children[index : index + int(replacing)] = incoming
        for child in incoming:
            child._parent = self
            if child.ownerDocument is not document:
                child._set_document(document)

    def appendChild(self, node: Node) -> Node:
        self._insert(node, None)
        return node

    def insertBefore(self, node: Node, reference: Node | None) -> Node:
        self._insert(node, reference)
        return node

    def replaceChild(self, node: Node, old: Node) -> Node:
        if not isinstance(old, Node):
            raise TypeError("Expected a Node")
        self._insert(node, old, replacing=True)
        return old

    def removeChild(self, node: Node) -> Node:
        if not isinstance(node, Node):
            raise TypeError("Expected a Node")
        if node._parent is not self:
            raise ValueError("Node is not a child of this parent")
        self._children.remove(node)
        node._parent = None
        return node


class ElementContainer(ParentNode):
    def getElementsByTagName(self, tag: str) -> _LiveCollection[Element]:
        if tag == "*":
            return _LiveCollection(self._elements)
        lower = ascii_lower(tag)
        return _LiveCollection(
            lambda: (
                node
                for node in self._elements()
                if node.localName
                == (lower if node.namespaceURI == HTML_NAMESPACE else tag)
            )
        )

    def getElementsByClassName(self, class_name: str) -> _LiveCollection[Element]:
        classes = set(tokens(class_name))
        if not classes:
            return _LiveCollection(tuple)

        def members():
            document = (
                self if self.nodeType == self.DOCUMENT_NODE else self.ownerDocument
            )
            if document is not None and document.compatMode == "BackCompat":
                folded = {ascii_lower(token) for token in classes}
                return (
                    node
                    for node in self._elements()
                    if folded.issubset(map(ascii_lower, node.classList))
                )
            return (
                node for node in self._elements() if classes.issubset(node.classList)
            )

        return _LiveCollection(members)

    def getElementsByTag(self, tag: str) -> list[Element]:
        return list(self.getElementsByTagName(tag))

    def getElementsByClass(self, class_name: str) -> list[Element]:
        return list(self.getElementsByClassName(class_name))


class DocumentFragment(ParentNode):
    nodeName = "#document-fragment"
    nodeType = Node.DOCUMENT_FRAGMENT_NODE

    def __init__(self) -> None:
        super().__init__()
        self._host: Element | None = None

    def getElementById(self, id: str) -> Element | None:
        if not id:
            return None
        return next((node for node in self._elements() if node.id == id), None)


class ClassList(Sequence[str]):
    """An ordered view of an element's class attribute."""

    def __init__(self, element: Element) -> None:
        self._element = element

    @property
    def value(self) -> str:
        return self._element.className

    @value.setter
    def value(self, value: str) -> None:
        self._element.className = value

    def __iter__(self) -> Iterator[str]:
        return iter(tokens(self.value))

    def __getitem__(self, index):
        return tokens(self.value)[index]

    def __len__(self) -> int:
        return len(tokens(self.value))

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def _validate(*values: str) -> None:
        for value in values:
            if not isinstance(value, str):
                raise TypeError("Expected a string class token")
            if not value or any(char in HTML_WHITESPACE for char in value):
                raise ValueError(
                    "Class tokens must be nonempty and contain no HTML whitespace"
                )

    def contains(self, value: str) -> bool:
        return value in self

    def add(self, *values: str) -> None:
        self._validate(*values)
        self.value = " ".join(dict.fromkeys([*self, *values]))

    def remove(self, *values: str) -> None:
        self._validate(*values)
        if self._element.hasAttribute("class"):
            self.value = " ".join(value for value in self if value not in values)

    def toggle(self, value: str, force: bool | None = None) -> bool:
        self._validate(value)
        present = value in self
        if force is None:
            force = not present
        if force and not present:
            self.add(value)
        if not force and present:
            self.remove(value)
        return bool(force)

    def replace(self, old: str, new: str) -> bool:
        self._validate(old, new)
        if old not in self:
            return False
        self.value = " ".join(
            dict.fromkeys(new if value == old else value for value in self)
        )
        return True


class Element(ElementContainer):
    nodeType = Node.ELEMENT_NODE

    def __init__(
        self,
        tag: str = "html",
        attributes: dict[str, str] | None = None,
        *,
        namespace: str = HTML_NAMESPACE,
    ) -> None:
        super().__init__()
        self._tag = ascii_lower(tag) if namespace == HTML_NAMESPACE else tag
        self._namespace = namespace
        self.attributes = dict(attributes or {})
        self._template_content = None
        if self.tag == "template" and self.namespaceURI == HTML_NAMESPACE:
            self._template_content = DocumentFragment()
            self._template_content._host = self

    @property
    def tag(self) -> str:
        return self._tag

    localName = tag

    @property
    def namespaceURI(self) -> str:
        return self._namespace

    @property
    def tagName(self) -> str:
        if self.namespaceURI == HTML_NAMESPACE:
            return self.tag.translate(_ASCII_UPPER)
        return self.tag

    nodeName = tagName

    @property
    def templateContent(self) -> DocumentFragment | None:
        return self._template_content

    @property
    def content(self) -> DocumentFragment | str:
        if self.templateContent is not None:
            return self.templateContent
        return self.innerHTML

    @property
    def innerHTML(self) -> str:
        from .serialization import serialize_children

        return serialize_children(self)

    @innerHTML.setter
    def innerHTML(self, markup: str | None) -> None:
        from .parser import DompyParser

        fragment = DompyParser.parseFragment(
            "" if markup is None else markup,
            context=self,
            scripting=self.ownerDocument._scripting
            if self.ownerDocument is not None
            else False,
        )
        target = self if self.templateContent is None else self.templateContent
        target._replace_children(fragment._children)
        fragment._children.clear()

    @property
    def outerHTML(self) -> str:
        from .serialization import serialize

        return serialize(self)

    @property
    def previousElementSibling(self) -> Element | None:
        node = self.previousSibling
        while node is not None and not isinstance(node, Element):
            node = node.previousSibling
        return node

    @property
    def nextElementSibling(self) -> Element | None:
        node = self.nextSibling
        while node is not None and not isinstance(node, Element):
            node = node.nextSibling
        return node

    def _attribute_name(self, name: str) -> str:
        return ascii_lower(name) if self.namespaceURI == HTML_NAMESPACE else name

    def getAttribute(self, name: str) -> str | None:
        return self.attributes.get(self._attribute_name(name))

    def hasAttribute(self, name: str) -> bool:
        return self._attribute_name(name) in self.attributes

    def setAttribute(self, name: str, value: str) -> None:
        if not name or any(char in HTML_WHITESPACE + "\x00\"'/>=" for char in name):
            raise ValueError("Invalid attribute name")
        self.attributes[self._attribute_name(name)] = str(value)

    def removeAttribute(self, name: str) -> None:
        self.attributes.pop(self._attribute_name(name), None)

    @property
    def id(self) -> str:
        return self.getAttribute("id") or ""

    @id.setter
    def id(self, value: str) -> None:
        self.setAttribute("id", value)

    @property
    def className(self) -> str:
        return self.getAttribute("class") or ""

    @className.setter
    def className(self, value: str) -> None:
        self.setAttribute("class", value)

    @cached_property
    def classList(self) -> ClassList:
        return ClassList(self)

    def matches(self, selector: str) -> bool:
        from .selectors import match

        return match(self, selector)

    def closest(self, selector: str) -> Element | None:
        from .selectors import closest

        return closest(self, selector)

    def _copy(self) -> Element:
        return Element(self.tag, self.attributes, namespace=self.namespaceURI)

    def __str__(self) -> str:
        return self.outerHTML


class Tags:
    DIV = "div"
    LI = "li"
    UL = "ul"
    HEADER = "header"
    FOOTER = "footer"
    TITLE = "title"
    HTML = "html"
    BODY = "body"
    HEAD = "head"
    META = "meta"
    LINK = "link"
    INPUT = "input"
    LABEL = "label"
    SPAN = "span"
    NAV = "nav"
    IMG = "img"
    H1 = "h1"
    H2 = "h2"
    H3 = "h3"
    H4 = "h4"
    H5 = "h5"
    H6 = "h6"
    P = "p"
    A = "a"
    MAIN = "main"
    SECTION = "section"
    I = "i"  # noqa: E741
    B = "b"
    VIDEO = "video"
    AUDIO = "audio"
    SOURCE = "source"
    FIGURE = "figure"
    FIG_CAPTION = "figcaption"
    BUTTON = "button"
    AREA = "area"
    BASE = "base"
    BR = "br"
    EMBED = "embed"
    HR = "hr"
    IFRAME = "iframe"
    PARAM = "param"
    TRACK = "track"
    COMMAND = "command"

    selfClosingTags = frozenset(
        {
            AREA,
            BASE,
            BR,
            "col",
            EMBED,
            HR,
            IMG,
            INPUT,
            LINK,
            META,
            PARAM,
            SOURCE,
            TRACK,
            "wbr",
            "basefont",
            "bgsound",
            "frame",
            "keygen",
        }
    )
