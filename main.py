from pathlib import Path

from dompy import Document

if __name__ == "__main__":
    document = Document.fromFile(Path(__file__).with_name("index.html"))
    print(document.title)
