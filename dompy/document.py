import requests
from typing import List, Dict, IO
from .models import Element, Tags
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
        for element in self.root.children:
            if element.tag == Tags.TITLE:
                self.title = element.innerHTML
                break
    
    def getElementById(self, id: str) -> Element:
        for element in self.root.children:
            if element.id == id:
                return element
        return None

    def getElementsByClass(self, className: str) -> List[Element]:
        result = []
        for element in self.root.children:
            if className in element.classList:
                result.append(element)
        return result

    def getElementsByTag(self, tag):
        result = []
        for element in self.root.children:
            if element.tag == tag:
                result.append(element)
        return result

    @classmethod
    def fromURL(cls, url):
        return cls(DompyParser.parse(requests.get(url).text))

    @classmethod
    def fromURI(cls, uri):
        raise Exception("Not Implemented Yet!")        

    @classmethod
    def fromString(cls, string):
        return cls(DompyParser.parse(string))

    @classmethod
    def fromFile(cls, file: IO):
        return cls(DompyParser.parse(file.read()))
