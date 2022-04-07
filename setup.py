from os import path
from setuptools import setup
from setuptools import find_packages

current_path = path.abspath(path.dirname(__file__))

def get_version():
  with open(path.join(current_path, 'VERSION')) as f:
      return f.read().strip()
  return "1.0.0"

setup(
  name='autosubmit_api',
  version=get_version(),
  description='An extension to the Autosubmit package that serves its information as an API',
  url='https://earth.bsc.es/gitlab/wuruchi/autosubmit_api',
  author='Wilmer Uruchi',
  author_email='wilmer.uruchi@bsc.es',
  license='GNU GPL',
  packages=find_packages(),
  keywords=['autosubmit', 'API'],
  python_requires='>=2.6, !=3.*',
  install_requires=['bscearth.utils==0.5.2',
                    'Flask==1.1.1',
                    'Flask-Cors==3.0.8',
                    'Flask-Jsonpify==1.5.0',
                    'Flask-RESTful==0.3.7',
                    'gunicorn==19.9.0',
                    'mock==3.0.5',
                    'networkx==2.2',
                    'numpy',
                    'paramiko==1.15.0',
                    'portalocker==0.5.7',
                    'pydotplus==2.0.2',
                    'regex',
                    'requests==2.22.0',
                    'graphviz==0.13',
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
    'Programming Language :: Python :: 2.7',
  ],
)