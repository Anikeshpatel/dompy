from dompy import Document

if __name__ == "__main__":
    # file = open('index.html', 'r')
    # document = Document.fromFile(file)
    # document.title
    # document.getElementById('header')
    # file.close()

    token = '<input type="checkbox" class="navigation__checkbox" id="navi-toggle">'
    for t in token.split(' '):
        if t.find('<') > -1:
            tag = t[t.find('<') +1 : len(t)]
            print(tag)
        elif t.find('='):
            key = t.split('=')[0]
            value = t.split('=')[1].replace('"', '').replace('>', '')
            print({key: value})
        
