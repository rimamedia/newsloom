import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'NewLoom'
copyright = '2024, RimaMedia'
author = 'RimaMedia'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'alabaster'
html_static_path = ['_static']

html_theme_options = {
    'description': 'A Django-based web scraping and content aggregation system',
    'github_user': 'rimamedia',
    'github_repo': 'newsloom',
    'github_button': True,
    'github_type': 'star',
    'fixed_sidebar': True,
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': ('https://docs.djangoproject.com/en/stable/', 'https://docs.djangoproject.com/en/stable/_objects/'),
    'luigi': ('https://luigi.readthedocs.io/en/stable/', None),
} 