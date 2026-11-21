"""Full HTML documents and input sources."""

from __future__ import annotations

import re
from os import PathLike
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname, urlopen

from .models import (
    HTML_NAMESPACE,
    Comment,
    DocumentFragment,
    DocumentType,
    Element,
    ElementContainer,
    Node,
    Text,
)
from .parser import _convert, _parse
from .serialization import serialize

_TITLE_WHITESPACE = re.compile(r"[ \t\n\r\f]+")
_INVALID_TAG_NAME = re.compile(r"[ \t\n\r\f\x00<>/]")


class Document(ElementContainer):
    """An inert HTML DOM built from a string, stream, file, or URL."""

    nodeName = "#document"
    nodeType = Node.DOCUMENT_NODE

    def __init__(self, root: Element | None = None, *, scripting: bool = False) -> None:
        super().__init__()
        self._scripting = scripting
        self._mode = "no-quirks"
        self._template_document = None
        if root is not None:
            self.appendChild(root)

    @property
    def documentElement(self) -> Element | None:
        return self.firstElementChild

    root = documentElement

    @property
    def compatMode(self) -> str:
        return "BackCompat" if self._mode == "quirks" else "CSS1Compat"

    @property
    def doctype(self) -> DocumentType | None:
        return next(
            (child for child in self._children if isinstance(child, DocumentType)), None
        )

    def _html_child(self, *tags):
        root = self.documentElement
        if root is None or root.namespaceURI != HTML_NAMESPACE or root.tag != "html":
            return None
        return next(
            (
                node
                for node in root.children
                if node.namespaceURI == HTML_NAMESPACE and node.tag in tags
            ),
            None,
        )

    @property
    def head(self) -> Element | None:
        return self._html_child("head")

    @property
    def body(self) -> Element | None:
        return self._html_child("body", "frameset")

    @property
    def title(self) -> str:
        for element in self._elements():
            if element.namespaceURI == HTML_NAMESPACE and element.tag == "title":
                return _TITLE_WHITESPACE.sub(" ", element.textContent).strip(" ")
        return ""

    @property
    def textContent(self) -> None:
        return None

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        pass

    def getElementById(self, id: str) -> Element | None:
        if not id:
            return None
        return next((node for node in self._elements() if node.id == id), None)

    def createElement(self, tag: str) -> Element:
        if not tag or _INVALID_TAG_NAME.search(tag):
            raise ValueError("Invalid element name")
        return self._create(Element(tag))

    def createTextNode(self, data: str) -> Text:
        return self._create(Text(data))

    def createComment(self, data: str) -> Comment:
        return self._create(Comment(data))

    def createDocumentFragment(self) -> DocumentFragment:
        return self._create(DocumentFragment())

    def _create(self, node):
        node._set_document(self)
        return node

    def _template_owner(self):
        if self._template_document is None:
            inert = Document()
            inert._template_document = inert
            self._template_document = inert
        return self._template_document

    @staticmethod
    def _validate_children(children):
        structure = [
            node.nodeType
            for node in children
            if node.nodeType
            not in (Node.COMMENT_NODE, Node.PROCESSING_INSTRUCTION_NODE)
        ]
        if structure not in (
            [],
            [Node.ELEMENT_NODE],
            [Node.DOCUMENT_TYPE_NODE],
            [Node.DOCUMENT_TYPE_NODE, Node.ELEMENT_NODE],
        ):
            raise ValueError(
                "A document may only contain one element and one preceding doctype"
            )

    def _copy(self) -> Document:
        clone = type(self)(scripting=self._scripting)
        clone._mode = self._mode
        return clone

    def __str__(self) -> str:
        return serialize(self)

    @classmethod
    def fromString(
        cls, string, *, scripting: bool = False, encoding: str | None = None
    ) -> Document:
        source, mode = _parse(string, scripting=scripting, encoding=encoding)
        doc = cls(scripting=scripting)
        doc._mode = mode
        _convert(source, doc)
        return doc

    @classmethod
    def fromFile(
        cls, file, *, scripting: bool = False, encoding: str | None = None
    ) -> Document:
        if isinstance(file, (str, PathLike)):
            return cls.fromString(
                Path(file).read_bytes(), scripting=scripting, encoding=encoding
            )
        return cls.fromString(file.read(), scripting=scripting, encoding=encoding)

    @classmethod
    def fromURL(
        cls, url: str, *, timeout: float = 30, scripting: bool = False
    ) -> Document:
        if urlsplit(url).scheme.lower() not in ("http", "https"):
            raise ValueError("fromURL expects an HTTP or HTTPS URL")
        with urlopen(url, timeout=timeout) as response:
            return cls.fromString(
                response.read(),
                scripting=scripting,
                encoding=response.headers.get_content_charset(),
            )

    @classmethod
    def fromURI(
        cls, uri: str, *, timeout: float = 30, scripting: bool = False
    ) -> Document:
        location = urlsplit(uri)
        if location.scheme in ("http", "https"):
            return cls.fromURL(uri, timeout=timeout, scripting=scripting)
        if location.scheme == "file" and location.netloc.lower() in ("", "localhost"):
            return cls.fromFile(url2pathname(location.path), scripting=scripting)
        raise ValueError("fromURI expects an HTTP(S) URL or a local file URI")
