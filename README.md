# lambda-setuptools

####A Command extension to setuptools that builds an AWS Lambda compatible zip file

Use is simple:

1. Add this **setup_requires=['lambda_setuptools']** as an attribute to your _setup.py_ file
2. Call **python setup.py _ldist_**
    * This will build (using bdist_wheel) and install your package, along with all of the dependencies in _install_requires_
    * Zip the result up into an AWS Lambda compatible format
        * The result will be in _dist/[your-package-name]-lambda-[version].zip_ (along with your wheel)


This extension also adds three new attributes to the setup() function:

1. lambda_function
    * Usage: _lambda_function=<my_package>.<some_module>:<some_function>_
    * Effect: ldist will create a root-level python module named *<package_name>_function.py* where package_name is derived from the _name_ attribute. This created module will simply redefine your lambda handler function at the root-level.
2. lambda_module
    * Usage: _lambda_module=<some_module>_
    * Effect: ldist adds the named module to the list of _py_modules_ to install, normally at the root level
3. lambda_package
    * Usage: _lambda_package=<some_dir>_
    * Effect: ldist will copy the contents of the provided directory into the root level of the resulting lambda distribution. The provided directory **MUST NOT** have and *\_\_init__.py* in it (e.g. - it can't be a real package)

All ldist attributes can be used in the same setup() call. It is up to the user to ensure that you don't step all over yourself...

Note that all other commands and attributes in setup.py will still work the way you expect them to.

Enjoy!

