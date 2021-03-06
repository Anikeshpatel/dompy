<p align='center'><img src="https://raw.githubusercontent.com/Anikeshpatel/dompy/master/docs/assets/logos/Group%205.png" /></p>
<!-- # Dompy -->
JavaScript Dom Api for Python, Html Parser and a Web scraping tool in python

##### Installation
```bash
pip install dompy-parser
```

##### Basic API

```python
>>> from dompy import Document
>>> document = Document.fromURL('https://www.lipsum.com')
>>> document.title
'Lorem Ipsum - All the facts - Lipsum generator'
>>> elements = document.getElementsByTag('h3')
>>> len(elements)
5
>>> elements[0].innerHTML
'The standard Lorem Ipsum passage, used since the 1500s'
```
<!-- **<center> or </center>** -->
**<p align='center'>or<p>**

```python
>>> from dompy import DompyParser
>>> document = DompyParser.parse('<div><h3 color="blue" align="center">Abc</h3><h3>Xyz</h3></div>')
>>> elements = document.getElementsByTag('h3')
>>> len(elements)
2
>>> elements[0].innerHTML
'Abc'
>>> elements[0].attributes
{'color': 'blue', 'align': 'center'}
```
___

#### License
Dompy is GNU GPL v3.0 licensed, as found in the LICENSE file.
