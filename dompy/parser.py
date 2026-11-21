"""HTML5 document and contextual fragment parsing."""

from justhtml import Element as ParsedElement
from justhtml.parser.context import FragmentContext
from justhtml.parser.encoding import decode_html
from justhtml.parser.engine import ParseEngine, compile_raw_engine_plan

from .models import (
    HTML_NAMESPACE,
    MATHML_NAMESPACE,
    SVG_NAMESPACE,
    Comment,
    DocumentFragment,
    DocumentType,
    Element,
    Node,
    ProcessingInstruction,
    Text,
    ascii_lower,
)

NAMESPACES = {"html": HTML_NAMESPACE, "svg": SVG_NAMESPACE, "math": MATHML_NAMESPACE}
PARSER_NAMESPACES = {uri: prefix for prefix, uri in NAMESPACES.items()}


class _TreeBuilder(ParseEngine):
    """Seed contextual HTML parser state unavailable through JustHTML's public API."""

    # The fragment context node is allocated just before the first token.
    def _parse_range(self, pos, end):
        if pos == 0 and self.context_encoding is not None:
            self._fragment_context_node.attrs["encoding"] = self.context_encoding
        return super()._parse_range(pos, end)


def _parse(
    markup,
    *,
    scripting=False,
    encoding=None,
    context=None,
    inside_form=False,
    context_encoding=None,
    document_mode=None,
):
    if isinstance(markup, (bytes, bytearray, memoryview)):
        markup, _ = decode_html(bytes(markup), transport_encoding=encoding)
    if not isinstance(markup, str):
        raise TypeError("HTML input must be text or bytes")

    html_context = context is not None and context.namespace == "html"
    # Fragment parsing in an HTML root starts in the document's before-head
    # insertion mode. Use the document shell and unwrap it after parsing.
    html_shell = html_context and context.tag_name == "html"
    fragment = context is not None and not html_shell
    engine = _TreeBuilder(
        markup,
        fragment=fragment,
        fragment_context=context if fragment else None,
        scripting_enabled=scripting,
        plan=compile_raw_engine_plan(fragment=fragment, scripting_enabled=scripting),
    )
    engine.context_encoding = context_encoding
    if context is not None:
        engine._quirks_mode = document_mode if document_mode else "no-quirks"
    if html_context and context.tag_name == "template":
        engine._enter_template_mode()
    if inside_form:
        engine._form_element = ParsedElement("form", {}, "html")
    root = engine.parse()
    if html_shell:
        root.children = [
            child
            for node in root.children
            for child in (node.children if node.name == "html" else [node])
        ]
    return root, engine._quirks_mode or "quirks"


def _convert(source, target):
    """Copy the parsed tree without recursing into the Python call stack."""
    stack = [(source, target)]
    while stack:
        parsed, parent = stack.pop()
        owner = (
            parent if parent.nodeType == Node.DOCUMENT_NODE else parent.ownerDocument
        )
        for child in parsed.children or ():
            if child.name == "#text":
                node = Text(child.data)
            elif child.name == "#comment":
                node = Comment(child.data)
            elif child.name == "#processing-instruction":
                target_name, _, data = child.data.partition(" ")
                node = ProcessingInstruction(target_name, data)
            elif child.name == "!doctype":
                info = child.data
                node = DocumentType(
                    info.name or "", info.public_id or "", info.system_id or ""
                )
            else:
                attributes = {name: value or "" for name, value in child.attrs.items()}
                node = Element(
                    child.name, attributes, namespace=NAMESPACES[child.namespace]
                )
                stack.append((child, node))
                if node.templateContent is not None:
                    node.templateContent._document = (
                        owner._template_owner() if owner else None
                    )
                    stack.append((child.template_content, node.templateContent))
            node._document = owner
            parent._append(node)


class DompyParser:
    @classmethod
    def parse(cls, input, *, scripting=False, encoding=None) -> Element:
        """Parse a document and return its HTML root element."""
        from .document import Document

        return Document.fromString(
            input, scripting=scripting, encoding=encoding
        ).documentElement

    @classmethod
    def parseFragment(
        cls,
        markup,
        context: str | Element = "div",
        *,
        scripting: bool = False,
        encoding: str | None = None,
    ) -> DocumentFragment:
        """Parse markup in an HTML, SVG, or MathML element context."""
        if isinstance(context, Element):
            tag = context.localName
            namespace = PARSER_NAMESPACES.get(context.namespaceURI, "html")
            owner = context.ownerDocument
            context_encoding = (
                context.getAttribute("encoding")
                if tag == "annotation-xml" and namespace == "math"
                else None
            )
            ancestor = context
            while ancestor is not None:
                if ancestor.tag == "form" and ancestor.namespaceURI == HTML_NAMESPACE:
                    break
                ancestor = ancestor.parentElement
            inside_form = ancestor is not None
        elif isinstance(context, str) and context:
            tag = ascii_lower(context)
            namespace = "html"
            owner = None
            context_encoding = None
            inside_form = tag == "form"
        else:
            raise TypeError("Fragment context must be a tag name or an Element")

        # Both contexts use RCDATA. A fragment has no opening textarea token
        # that would cause the parser to discard an initial line feed.
        if tag == "textarea" and namespace == "html":
            tag = "title"
        source, _ = _parse(
            markup,
            context=FragmentContext(tag, namespace),
            scripting=scripting,
            encoding=encoding,
            inside_form=inside_form,
            context_encoding=context_encoding,
            document_mode=owner._mode if owner is not None else None,
        )
        fragment = DocumentFragment()
        fragment._document = owner
        _convert(source, fragment)
        return fragment
