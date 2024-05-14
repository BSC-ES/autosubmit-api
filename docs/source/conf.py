# Configuration file for the Sphinx documentation builder.

# -- Project information

project = "Autosubmit API"
copyright = "2024, Barcelona Supercomputing Center, BSC"
author = "Earth Sciences Department, Barcelona Supercomputing Center, BSC"

release = "4.0.0"
version = "4.0.0"

# -- General configuration

extensions = [
    'sphinxcontrib.redoc'
]

# -- Options for HTML output

redoc = [
    {
        'name': 'Autosubmit API',
        'page': 'api',
        'spec': '_static/openapi.json',
        # 'spec': 'https://petstore3.swagger.io/api/v3/openapi.json',
        # 'spec': 'https://petstore.swagger.io/v2/swagger.json'
        'opts': {
            'suppress-warnings': True,
            'hide-hostname': True
        }
    }
]

html_theme = "pydata_sphinx_theme"

html_static_path = ["_static"]

html_logo = "_static/Logo.svg"

html_css_files = ["custom.css"]
