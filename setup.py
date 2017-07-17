import sys
from setuptools import setup

import transloadit


install_requires = ['requests==2.11.1', 'six==1.10.0', 'tuspy==0.1']

PY_VERSION = sys.version_info[0], sys.version_info[1]
if PY_VERSION < (3, 0):
    long_description = open('README.md').read()
else:
    long_description = open('README.md', encoding='utf-8').read()

setup(
    name='pytransloadit',
    version=transloadit.__version__,
    url='http://github.com/transloadit/python-sdk/',
    license='MIT',
    author='Ifedapo Olarewaju',
    install_requires=install_requires,
    author_email='ifedapoolarewaju@gmail.com',
    description="A **Python** Integration for [Transloadit](https://transloadit.com)'s file uploading and encoding service.",
    long_description=(long_description),
    packages=['transloadit'],
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Programming Language :: Python',
        'Natural Language :: English',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Topic :: Communications :: File Sharing',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Multimedia :: Sound/Audio :: Conversion'
    ]
)
