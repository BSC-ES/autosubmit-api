from os import path
from setuptools import setup
from setuptools import find_packages
from pathlib import Path
import autosubmit_api

current_path = path.abspath(path.dirname(__file__))

# read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def get_version():
    return autosubmit_api.__version__


def get_authors():
    return autosubmit_api.__author__


install_requires = [
    "fastapi[all]==0.115.0",
    "Flask~=2.2.5",
    "pyjwt~=2.8.0",
    "requests~=2.28.1",
    "flask_cors~=3.0.10",
    "bscearth.utils~=0.5.2",
    "pydotplus~=2.0.2",
    "portalocker~=2.6.0",
    "networkx<=2.6.3",
    "scipy~=1.11.4",
    "python-dotenv~=1.0.1",
    "autosubmitconfigparser>=1.0.65",
    "autosubmit>=3.13",
    "APScheduler~=3.10.4",
    "gunicorn~=22.0.0",
    "pydantic~=2.5.2",
    "SQLAlchemy~=2.0.23",
    "python-cas~=1.6.0"
]

# Test dependencies
test_requires = [
    "pytest",
    "pytest-cov",
    "pytest-asyncio",
    "ruff"
]

extras_require = {
    'test': test_requires,
    'all': install_requires + test_requires
}

setup(
    name="autosubmit_api",
    version=get_version(),
    description="An extension to the Autosubmit package that serves its information as an API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://earth.bsc.es/gitlab/es/autosubmit_api",
    author=get_authors(),
    author_email="support-autosubmit@bsc.es",
    license="GNU GPL",
    packages=find_packages(),
    keywords=["autosubmit", "API"],
    python_requires=">=3.9",
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    package_data={"autosubmit-api": ["README", "VERSION", "LICENSE"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "console_scripts": [
            "autosubmit_api = autosubmit_api.cli:main",
        ]
    },
)
