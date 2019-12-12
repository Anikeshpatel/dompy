from .models import Element

class DompyParser:
    @staticmethod
    def parse(input):
        position = 0
        for token in input:
            position += 1
            if token == '<' and input[position + 1] != '!':
                print(input[position: input.find('>', position)])

    @staticmethod
    def __resolveTag(tagToken: str) -> Element:
        children = []
        if (hasChildren(tagToken)):
            for child in parseChildren(tagToken):
                children.append(DompyParser.__resolveTag(child))
        element = parseTag(tagToken)
        element.children = children
        return element

