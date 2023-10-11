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
  install_requires=['jwt==1.3.1',
			'requests==2.28.1',
			'flask_cors==3.0.10',
			'bscearth.utils==0.5.2',
			'pysqlite-binary',
			'numpy==1.21.6',
			'pydotplus==2.0.2',
			'portalocker==2.6.0',
			'networkx==2.6.3',
			'scipy==1.7.3',
			'paramiko==2.12.0',
      'python-dotenv',
      'autosubmitconfigparser==1.0.48'
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
)
