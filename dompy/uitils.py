"""Legacy utility imports."""

from .models import Node


def hasChildren(node: Node) -> bool:
    return node.hasChildNodes()
