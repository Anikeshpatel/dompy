"""Compact HTML serialization of the current tree."""

from .models import (
    HTML_NAMESPACE,
    Comment,
    DocumentType,
    Element,
    ProcessingInstruction,
    Tags,
    Text,
)

_RAW_TEXT = frozenset(
    {"iframe", "noembed", "noframes", "plaintext", "script", "style", "xmp"}
)
_TEXT_ESCAPES = str.maketrans(
    {"&": "&amp;", "\xa0": "&nbsp;", "<": "&lt;", ">": "&gt;"}
)
_ATTRIBUTE_ESCAPES = str.maketrans(
    {"&": "&amp;", "\xa0": "&nbsp;", '"': "&quot;", "<": "&lt;", ">": "&gt;"}
)


def _markup_children(node):
    if isinstance(node, Element) and node.templateContent is not None:
        return node.templateContent._children
    return node._children


def _raw_text(parent):
    if not isinstance(parent, Element) or parent.namespaceURI != HTML_NAMESPACE:
        return False
    if parent.tag == "noscript":
        return parent.ownerDocument is not None and parent.ownerDocument._scripting
    return parent.tag in _RAW_TEXT


def _serialize_nodes(nodes):
    parts = []
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, Element):
            attributes = "".join(
                f' {name}="{value.translate(_ATTRIBUTE_ESCAPES)}"'
                for name, value in node.attributes.items()
            )
            parts.append(f"<{node.tag}{attributes}>")
            if (
                node.namespaceURI != HTML_NAMESPACE
                or node.tag not in Tags.selfClosingTags
            ):
                stack.append(f"</{node.tag}>")
                stack.extend(reversed(_markup_children(node)))
        elif isinstance(node, Text):
            parts.append(
                node.data
                if _raw_text(node.parentNode)
                else node.data.translate(_TEXT_ESCAPES)
            )
        elif isinstance(node, Comment):
            parts.append(f"<!--{node.data}-->")
        elif isinstance(node, DocumentType):
            parts.append(f"<!DOCTYPE {node.name}>")
        elif isinstance(node, ProcessingInstruction):
            parts.append(f"<?{node.target} {node.data}?>")
        else:
            stack.extend(reversed(node._children))
    return "".join(parts)


def serialize(node):
    return _serialize_nodes([node])


def serialize_children(node):
    return _serialize_nodes(_markup_children(node))
