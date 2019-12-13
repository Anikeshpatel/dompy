from dompy import Document

if __name__ == "__main__":
    file = open('index.html', 'r')
    document = Document.fromURL('https://www.lipsum.com')
    # OR
    # document = Document.fromFile(file)
    print(document.title)
    file.close()
