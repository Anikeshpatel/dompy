import re
from .models import Element, Tags

class DompyParser:

    @classmethod
    def parse(cls, input):
        input = input.replace('<!DOCTYPE html>', '')
        input = re.sub('\s+', ' ', input)
        input = re.sub('\<\!\-\-(.)*\-\-\>', '', input)
        input = re.sub('\s+', ' ', input)
        input = input.lstrip()
        return cls.__resolveTag(input)
        # position = 0
        # for token in input:
        #     position += 1
        #     if token == '<' and input[position + 1] != '!' and input[position] != '/':
        #         print(input[position: input.find('>', position)])

    @classmethod
    def __resolveTag(cls, token: str) -> Element:
        tag = token[token.find('<') + 1 : token.find('>')].split(' ')[0]
        startIndex = token.find('<')
        endIndex = token.find('>', token.find(tag, startIndex + len(tag))) + 1

        # startIndex = token.find('<', startIndex + len(tag)) + 1
        # tag = token[startIndex : token.find('>', startIndex)].split(' ')[0]
        # endIndex = token.find('>', token.find(tag, startIndex + len(tag))) + 1
        # print(startIndex, endIndex)
        # print(tag)
        # print(token[startIndex - 1 : endIndex])

        children = []
        for child in cls.__parseChildren(tag, token):
            element = cls.__parseTag(child)
            if element.tag != Tags.HTML:
                children.append(element)
        element = Element()
        element.tag = 'html'
        element.children = children
        element.innerHTML = children
        return element
        # startIndex = token.find('<') + 1
        # endIndex = token.find('>', startIndex)
        # token = token[startIndex : endIndex]
        # element = cls.__parseTag(token)
        # element.children = children
        # return element

    @classmethod
    def __parseChildren(cls, tag, token):
        children = []
        if token.find('<', token.find(tag)) == -1:
            return children
        startIndex = len(tag)
        endIndex = 0
        while(startIndex != -1):
            startIndex = token.find(f'<', startIndex + 1)
            if token[startIndex + 1] == '/':
                continue
            if startIndex == -1:
                break
            tag = token[startIndex + 1 : token.find(">", startIndex)].split(" ")[0]
            endingToken = f'</{tag}>'
            endIndex = token.find(endingToken, token.find(tag, startIndex)) + len(endingToken)
            children.append(token[startIndex : endIndex])
        return children

    @classmethod
    def __parseTag(cls, token) -> Element:
        element = Element()
        element.innerHTML = token[token.find('>') + 1 : token.find('<', token.find('>') + 1)]
        element.content = element.innerHTML
        token = token[0 : token.find('>') + 1]
        for t in token.split(' '):
            if t.find('<') > -1:
                element.tag = t[t.find('<') + 1 : len(t)].replace('>', '')
            elif t.find('=') > -1:
                key = t.split('=')[0]
                value = t.split('=')[1].replace('"', '').replace('>', '')
                if key == 'id':
                    element.id = value
                elif key == 'class':
                    element.classList.append(value)
                else:
                    element.attributes[key] = value
        return element
