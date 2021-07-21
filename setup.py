from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))


def get_long_description():
    with open(
        path.join(path.dirname(path.abspath(__file__)), "README.md"), encoding="utf8"
    ) as fp:
        return fp.read()


setup(
    name="lambda-setuptools",
    version="0.6.0",
    description="A Command extension to setuptools that allows building an AWS Lamba dist and uploading to S3",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/QuiNovas/lambda-setuptools",
    author="Joseph Wortmann",
    author_email="joseph.wortmann@gmail.com",
    license="APL 2.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="setuptools extension",
    install_requires=["boto3", "setuptools", "wheel", "lambda-pkg-resources>=0.0.5"],
    package_dir={"": "src"},
    packages=find_packages("src"),
    setup_requires=[],
    entry_points={
        "distutils.commands": [
            "ldist = lambda_setuptools.ldist:LDist",
            "lupload = lambda_setuptools.lupload:LUpload",
            "lupdate = lambda_setuptools.lupdate:LUpdate",
        ],
        "distutils.setup_keywords": [
            "lambda_function = lambda_setuptools.ldist:validate_lambda_function",
            "lambda_module = lambda_setuptools.ldist:add_lambda_module_to_py_modules",
            "lambda_package = lambda_setuptools.ldist:validate_lambda_package",
        ],
    },
)
