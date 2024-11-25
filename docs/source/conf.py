# Configuration file for the Sphinx documentation builder.

# -- Project information

project = "Autosubmit API"
copyright = "2024, Barcelona Supercomputing Center, BSC"
author = "Barcelona Supercomputing Center"

release = "4.0.0"
version = "4.0.0"

# -- General configuration

extensions = ["sphinxcontrib.redoc"]

# -- Options for HTML output

redoc = [
    {
        "name": "Autosubmit API",
        "page": "api",
        "spec": "_static/openapi.json",
        # 'spec': 'https://petstore3.swagger.io/api/v3/openapi.json',
        # 'spec': 'https://petstore.swagger.io/v2/swagger.json'
        "opts": {"suppress-warnings": True, "hide-hostname": True},
    }
]

html_theme = "pydata_sphinx_theme"

html_static_path = ["_static"]

html_logo = "_static/Logo.svg"

html_css_files = ["custom.css"]

html_context = {
    "github_user": "BSC-ES",
    "github_repo": "autosubmit-api",
    "github_version": "main",
}

html_theme_options = {
    "header_links_before_dropdown": 6,
    "show_nav_level": 2,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/BSC-ES/autosubmit-api",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
}

# Add meta tags
html_meta = {
    "description": "Autosubmit API documentation",
    "keywords": "autosubmit, API, documentation, BSC-ES",
    "author": "BSC-ES",
}
