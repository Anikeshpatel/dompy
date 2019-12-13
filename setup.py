from distutils.core import setup
setup(
  name = 'dompy_parser',         # How you named your package folder (MyLib)
  packages = ['dompy'],   # Chose the same as "name"
  version = '0.1',      # Start with a small number and increase it with every change you make
  license='GNU General Public License v3.0',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
  description = 'JavaScript Dom Api for Python, Html Parser and a Web scraping library',   # Give a short description about your library
  author = 'Anikesh Patel',                   # Type in your name
  author_email = 'developeranikesh@gmail.com',      # Type in your E-Mail
  url = 'https://github.com/Anikeshpatel/dompy',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/Anikeshpatel/dompy/archive/0.1.zip',    # I explain this later on
  keywords = ['html parser', 'dompy parser', 'web scraping', 'javascript dom api', 'python dom', 'py dom'],   # Keywords that define your package best
  install_requires=[],
  classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8'
  ],
)
