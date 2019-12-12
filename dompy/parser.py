import re
from .models import Element

class DompyParser:
    @staticmethod
    def parse(input):
        input = input.replace('<!DOCTYPE html>', '')
        input = re.sub('\s+', ' ', input)
        input = re.sub('\<\!\-\-(.)*\-\-\>', '', input)
        input = re.sub('\s+', ' ', input)
        input = input.lstrip()
        with open('temp.html', 'w') as f:
            f.write(input)
        position = 0
        for token in input:
            position += 1
            if token == '<' and input[position + 1] != '!' and input[position] != '/':
                print(input[position: input.find('>', position)])

    @staticmethod
    def __resolveTag(cls, tagToken: str) -> Element:
        children = []
        for child in cls.__parseChildren(tagToken):
            children.append(DompyParser.__resolveTag(child))
        element = cls.__parseTag(tagToken)
        element.children = children
        return element

    @staticmethod
    def __parseChildren(token):
        pass

    @staticmethod
    def __parseTag(token) -> Element:
        element = Element()
        token = '<input type="checkbox" class="navigation__checkbox" id="navi-toggle">'
        for t in token.split(' '):
            if t.find('<') > -1:
                element.tag = t[t.find('<') +1 : len(t)]
            elif t.find('='):
                key = t.split('=')[0]
                value = t.split('=')[1].replace('"', '').replace('>', '')
                if key == 'id':
                    element.id = value
                elif key == 'class':
                    element.classList.append(value)
                else:
                    element.attributes[key] = value
        return element
