from typing import List, Dict, IO
from .models import Element
from .parser import DompyParser

class Document:
    """
    A class used to represent a HTML DOM or Document

    ...

    Attributes
    ----------
    root: Element
        The root element of the document usually <html> tag

    title: str
        The title of the document fetched from <title> tag inside <head> section

    Methods
    -------
    getElementById(id: str) -> Element
        Returns the first element with passed id

    getElementsByClass(className: str) -> List[Element]
        Returns the list of element with passed className

    getElementsByTag(tag: str) -> List[Element]
        Returns the list of element with passed tag
    """
    def __init__(self, root: Element):
        self.root = root
        self.title:str = ''
    
    def getElementById(self, id: str) -> Element:
        pass

    def getElementsByClass(self, className: str) -> List[Element]:
        pass

    def getElementsByTag(self, tag):
        pass

    @classmethod
    def fromURL(cls, url):
        pass

    @classmethod
    def fromURI(cls, uri):
        pass

    @classmethod
    def fromString(string):
        pass

    @classmethod
    def fromFile(cls, file: IO):
        return cls(DompyParser.parse(file.read()))
