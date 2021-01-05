# lambda-setuptools

#### A Command extension to setuptools that builds an AWS Lambda compatible zip file and uploads it to an S3 bucket

Simply add `setup_requires=['lambda_setuptools']` as an attribute to your _setup.py_ file

This extension adds two new commands to setuptools:

1. **ldist**
    * Usage: `ldist --exclude-lambda-packages=<True | true | Yes | yes | False | false | No | no> --include-version=<True | true | Yes | yes | False | false | No | no> --build-layer=<True | true | Yes | yes | False | false | No | no> --layer-dir=<my_layer_dir>`
        * Effect: This will build (using _bdist_wheel_) and install your package, along with all of the dependencies in _install_requires_
            * _exclude-lambda-packages_ is optional. If not present it will default to _True_. If _True_, all packages provided by the
            AWS Lambda execution environment will be excluded from your lambda function package
            * _include-version_ is optional. If not present it will default to _True_
            * _build-layer_ is optional. If not present it will default to _False_. Set to _True_ to build a layer instead of a function
            * _layer-dir_ is optional. Defaults to _python_. Only used if _build-layer_ is _True_
            * It is _highly_ recommended that you **DO NOT** include _boto3_ or _botocore_ in your _install_requires_ dependencies as these are provided by the AWS Lambda environment. Include them at your own peril! 
            * The result will be in _dist/[your-package-name]-[version].zip_ (along with your wheel)
2. **lupload**
    * Usage: `lupload --access-key=<my_access_key> --secret-access-key=<my_secret> --s3-bucket=<my_S3_bucket> --kms-key-id=<my_KMS_key> --s3-prefix=<my_S3_key_prefix> --endpoint-url=<my_endpoint_url>`
        * Effect: This will build (using _ldist_) and upload the resulting ZIP file to the specified S3 bucket
            * _access-key_ ans _secret-access-key_ are optional (and DEPRECATED). The new method of setting these is by using the boto3 standard (https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html). This allows for several methods of granting AWS access, including through the use of roles and assumed roles. If provided, these are set to **AWS_ACCESS_KEY_ID** and **AWS_SECRET_ACCESS_KEY** environment variables (respectively) in the local `os.environ`.
            * _kms-key-id_ is optional. If it is not provided, standard AES256 encryption will be used
            * _s3-prefix_ is optional. If it is not provided, the ZIP file will be uploaded to the root of the S3 bucket
            * _endpoint_url_ is optional. If it is not provided, the default endpoint for the accessed account will be used
3. **lupdate**
    * Usage: `lupdate --function-names=<my_function1>,<my_function2>,<my_function3> --lambda-names=<my_name1>,<my_name2>,<my_name3> --layer-runtimes=python2.7,python3.6,python3.7 --region=<my_aws_region>`
        * Effect: This will update the AWS Lambda function or layer code for the listed functions/layers. Functions/layers may be function names, partial ARNs (in the case of a function name) and/or full ARNs.
            * _function-names_ is *DEPRECATED*. Use _lambda-names_ instead. Joined as a _set_ with _lambda-names_.
            * _lambda-names_ contains the names of functions XOR layers, depending on the update type. Update type is sourced from _ldist_ through _lupload_.
            * _layer-runtimes_ is optional, and can be one or more of _python2.7_|_python3.6_|_python3.7_, seperated by commas. Defaults to all three.
            * Requires the use of *lupload* as the S3 object uploaded is used as the function/layer code to update.
            * _region_ is optional. If it is not provided, then `us-east-1` will be used.

This extension also adds three new attributes to the setup() function:

1. **lambda_function**
    * Usage: `lambda_function=<my_package>.<some_module>:<some_function>`
    * Effect: ldist will create a root-level python module named *<package_name>_function.py* where package_name is derived from the _name_ attribute. This created module will simply redefine your lambda handler function at the root-level
2. **lambda_module**
    * Usage: `lambda_module=<some_module>`
    * Effect: ldist adds the named module to the list of _py_modules_ to install, normally at the root level
3. **lambda_package**
    * Usage: `lambda_package=<some_dir>`
    * Effect: ldist will copy the contents of the provided directory into the root level of the resulting lambda distribution. The provided directory **MUST NOT** have an *\_\_init__.py* in it (e.g. - it can't be a real package)

All _ldist_ attributes can be used in the same setup() call. It is up to the user to ensure that you don't step all over yourself...

Note that all other commands and attributes in setup.py will still work the way you expect them to.

Enjoy!

