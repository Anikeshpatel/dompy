from typing import List, Dict, IO

class Element:
    def __init__(self):
        self.id = None
        self.tag = Tags.HTML
        self.children = []
        self.classList = []
        self.attributes: Dict[str, Any] = {}
        self.innerHTML = self.children
        self.content = ''

    def __str__(self):
        return f'<{self.tag}>: id=\'{self.id}\' class=\'{[className for className in self.classList]}\''

class Tags:
    DIV = 'div'
    LI = 'li'
    UL = 'ul'
    HEADER = 'header'
    FOOTER = 'footer'
    TITLE = 'title'
    HTML = 'html'
    BODY = 'body'
    HEAD = 'head'
    META = 'meta'
    LINK = 'link'
    INPUT = 'input'
    LABEL = 'label'
    SPAN = 'span'
    NAV = 'nav'
    IMG = 'img'
    H1 = 'h1'
    H2 = 'h2'
    H3 = 'h3'
    H4 = 'h4'
    H5 = 'h5'
    H6 = 'h6'
    P = 'p'
    A = 'a'
    MAIN = 'main'
    SECTION = 'section'
    I = 'i'
    B = 'b'
    VIDEO = 'video'
    AUDIO = 'audio'
    SOURCE = 'source'
    FIGURE = 'figure'
    FIG_CAPTION = 'figcaption'
    BUTTON = 'button'
