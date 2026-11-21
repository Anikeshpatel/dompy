# Dompy

Dompy turns HTML into an editable Python tree with browser-style DOM methods. It handles malformed markup, contextual fragments, mixed text, HTML templates, and SVG and MathML. Parsing is inert. Dompy preserves scripts and event-handler attributes as data and never executes them.

## Install

Dompy requires Python 3.10 or later.

```bash
python -m pip install dompy-parser
```

To install this checkout, run `python -m pip install .` from the project root.

## Parse, query, and edit

```python
from dompy import Document, DompyParser

document = Document.fromString("""
<!doctype html>
<title>Inventory</title>
<main id="inventory">
  <table><tr><td>Apples<td>5</table>
</main>
""")

table = document.querySelector("#inventory > table")
print(document.title)                                  # Inventory
print(table.querySelector("tbody > tr").textContent)    # Apples5

rows = table.getElementsByTagName("tr")
fragment = DompyParser.parseFragment("<tr><td>Pears<td>8", context="tbody")
table.querySelector("tbody").appendChild(fragment)
assert len(rows) == 2

cell = rows[1].querySelector("td")
cell.classList.add("product")
cell.textContent = "Green pears"
assert cell.outerHTML == '<td class="product">Green pears</td>'
```

- `Document.fromString(html)` accepts text or bytes. Byte input supports HTML charset sniffing and an optional `encoding`.
- `Document.fromFile(path_or_stream)` accepts paths and open binary or text streams. `Document.fromURL(url, timeout=30)` loads an HTTP(S) response and uses its declared charset when present. `Document.fromURI(uri)` also accepts local file URIs.
- `Document.documentElement` (also `root`), `head`, `body`, `doctype`, `title`, and `compatMode` describe the parsed document. Use `str(document)` to serialize it.
- `querySelector` and `querySelectorAll` accept CSS selectors, including combinators, attribute tests, `:scope`, `:is()`, and `:has()`. Queries return the first element or `None`, or a snapshot list in document order. Invalid or unsupported selectors raise `SelectorError`.
- `getElementById` matches exact IDs. `getElementsByTagName`, `getElementsByClassName`, `children`, and `childNodes` provide live sequences. `children` contains only elements. `childNodes` includes text and comments.
- Read markup with `innerHTML` and `outerHTML`, and read or write text with `textContent`. Assigning `innerHTML` parses markup in the target element's context. HTML template contents live in `template.content`, a separate `DocumentFragment`.
- Create and edit nodes with `createElement`, `createTextNode`, `createComment`, `createDocumentFragment`, `appendChild`, `insertBefore`, `replaceChild`, `removeChild`, and `cloneNode`. Elements also support `matches`, `closest`, and attribute and class operations.

`DompyParser.parse(html)` returns the root `Element`. The original `getElementsByTag` and `getElementsByClass` methods return Python lists. `Element.tag` exposes the local tag name, and `Element.content` returns `innerHTML` for regular elements.

Dompy implements a static HTML DOM. Layout, JavaScript execution, event dispatch, and resource loading from markup are outside its scope. `scripting=True` changes how the parser handles `<noscript>`. CSS matching uses Soup Sieve, with limited support for browser state and no pseudo-elements. Serialization preserves potentially active markup, so treat the output as unsanitized HTML.

## Test

```bash
python -m pip install -e '.[test]'
python -m pytest --cov=dompy
```

The browser suite compares Python trees, serialization, CSS queries, and fragment edits with Chromium's `DOMParser`. It runs offline once Chromium is installed.

```bash
python -m pip install -e '.[test,browser]'
python -m playwright install chromium
DOMPY_BROWSER=chromium python -m pytest
```

Set `DOMPY_BROWSER=chrome` to use a local Google Chrome installation.

## License

Dompy is licensed under the GNU GPL v3. See [LICENSE](LICENSE).
