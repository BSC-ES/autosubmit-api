from os import path
from setuptools import setup
from setuptools import find_packages

import autosubmit_api

current_path = path.abspath(path.dirname(__file__))


def get_version():
    return autosubmit_api.__version__

def get_authors():
    return autosubmit_api.__author__


setup(
    name='autosubmit_api',
    version=get_version(),
    description='An extension to the Autosubmit package that serves its information as an API',
    url='https://earth.bsc.es/gitlab/es/autosubmit_api',
    author=get_authors(),
    author_email='support-autosubmit@bsc.es',
    license='GNU GPL',
    packages=find_packages(),
    keywords=['autosubmit', 'API'],
    python_requires='>=3.7',
    install_requires=[
        'Flask~=2.2.5',
        'jwt~=1.3.1',
        'requests~=2.28.1',
        'flask_cors~=3.0.10',
        'bscearth.utils~=0.5.2',
        'pysqlite-binary',
        'numpy~=1.21.6',
        'pydotplus~=2.0.2',
        'portalocker~=2.6.0',
        'networkx~=2.6.3',
        'scipy~=1.7.3',
        'paramiko~=2.12.0',
        'python-dotenv',
        'autosubmitconfigparser~=1.0.48',
        'autosubmit>=3.13',
        'Flask-APScheduler',
        'gunicorn'
    ],
    include_package_data=True,
    package_data={'autosubmit-api': ['README',
                                     'VERSION',
                                     'LICENSE']},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': [
            'autosubmit_api = autosubmit_api.cli:main',
        ]
    }
)
