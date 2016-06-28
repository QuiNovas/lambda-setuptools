from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as readme:
    long_description = readme.read()

setup(
    name='lambda-setuptools',

    version='0.1.2',

    description='A Command extension to setuptools that allows building an AWS Lamba dist',
    long_description=long_description,

    url='https://github.com/illumicare/setuptools-lambda-dist-extension',

    author='Joseph Wortmann',
    author_email='joseph.wortmann@gmail.com',

    license='APL 2.0',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        ],

    keywords='setuptools extension',

    install_requires=['setuptools', 'wheel'],

    package_dir={'': 'src'},
    packages=find_packages('src'),

    entry_points={"distutils.commands": ['ldist = lambda_setuptools.ldist:LDist']}
)
