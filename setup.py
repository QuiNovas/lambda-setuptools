import pypandoc

from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as readme:
    long_description = readme.read()

# Convert the README.md to README.rst
with open('README.rst','w') as readme:
    readme.write(pypandoc.convert('README.md', 'rst', format='markdown'))

setup(
    name='lambda-setuptools',

    version='0.1.5',

    description='A Command extension to setuptools that allows building an AWS Lamba dist and uploading to S3',
    long_description=long_description,

    url='https://github.com/QuiNovas/lambda-setuptools',

    author='Joseph Wortmann',
    author_email='joseph.wortmann@gmail.com',

    license='APL 2.0',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        ],

    keywords='setuptools extension',

    install_requires=['boto3', 'setuptools', 'wheel', 'pypandoc'],

    package_dir={'': 'src'},
    packages=find_packages('src'),

    entry_points={
        'distutils.commands': [
            'ldist = lambda_setuptools.ldist:LDist',
            'lupload = lambda_setuptools.lupload:LUpload'
        ],
        'distutils.setup_keywords': [
            'lambda_function = lambda_setuptools.ldist:validate_lambda_function',
            'lambda_module = lambda_setuptools.ldist:add_lambda_module_to_py_modules',
            'lambda_package = lambda_setuptools.ldist:validate_lambda_package'
        ]
    }
)
