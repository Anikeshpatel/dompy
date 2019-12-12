from dompy import Document

if __name__ == "__main__":
    file = open('index.html', 'r')
    document = Document.fromFile(file)
    document.title
    document.getElementById('header')
    file.close()
