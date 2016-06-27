# setuptools-lambda-dist-extension
####A Command extension to setuptools that builds an AWS Lambda compatible zip file

Use is simple:
1. Add this **setup_requires=['lambda_setuptools']** as an attribute to your _setup.py_ file
2. Call **python setup.py _ldist_**
    * This will build (using bdist_wheel) and install your package, along with all of the dependencies in _install_requires_
    * Zip the result up into an AWS Lambda compatible format
        * The result will be in _dist/[your-package-name]-lambda-[version].zip_ (along with your wheel)

Note that all other commands and attributes in setup.py will still work the way you expect them to.

Enjoy!

