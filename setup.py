import sys
from setuptools import setup

import transloadit


install_requires = ["requests>=2.18.4", "six>=1.11.0", "tuspy>=0.2.3"]
tests_require = [
    "requests-mock>=1.3.0",
    "mock>=2.0.0",
    "coverage>=4.2",
    "pytest>=4.6",
    "pytest-cov>=2.3.1",
]

try:
    import pypandoc

    long_description = pypandoc.convert_file("README.md", "rst").replace("\r", "")
except (ImportError, OSError):  # pypandoc or pandoc is not installed
    long_description = ""

setup(
    name="pytransloadit",
    version=transloadit.__version__,
    url="http://github.com/transloadit/python-sdk/",
    license="MIT",
    author="Ifedapo Olarewaju",
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "test": tests_require,
        "dev": ["tox>=2.3.1", "sphinx-autobuild==0.7.1", "Sphinx==1.7.1"],
    },
    maintainer="Arnaud Limbourg",
    description="A Python Integration for https://transloadit.com file uploading and encoding service.",
    long_description=long_description,
    packages=["transloadit"],
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Natural Language :: English",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: File Transfer Protocol (FTP)",
        "Topic :: Communications :: File Sharing",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Multimedia :: Sound/Audio :: Conversion",
    ],
)
