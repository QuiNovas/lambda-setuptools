import boto3
import json
import os

from botocore.client import Config
from botocore.exceptions import ClientError
from distutils import log
from distutils.errors import DistutilsArgError, DistutilsOptionError
from os import environ
from setuptools import Command


class LUpdate(Command):
    description = 'Update the specified Lambda functions or layers with the result of the lupload command'
    user_options = [
        ('function-names=', None, 'DEPRECATED - use "lambda-names" instead. Comma seperated list of function names to update. Must have at least one entry. Can be function names, partial ARNs, and/or full ARNs'),
        ('lambda-names=', None, 'Comma seperated list of function or layer names to update. Must have at least one entry. Can be function/layer names, partial ARNs, and/or full ARNs'),
        ('layer-runtimes=', None, 'Comma seperated list of python runtimes the layer is compatible with. Defaults to "python2.7,python3.6,python3.7"'),
        ('region=', None, 'Region for the named lambda functions or layers. Defaults to AWS_DEFAULT_REGION if set, else "us-east-1"')
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        setattr(self, 'function_names', '')
        setattr(self, 'lambda_names', '')
        setattr(self, 'layer_runtimes', 'python2.7,python3.6,python3.7')
        setattr(self, 'region', environ.get('AWS_REGION', environ.get('AWS_DEFAULT_REGION', 'us-east-1')))

    def finalize_options(self):
        """Post-process options."""
        if not getattr(self, 'function_names') and not getattr(self, 'lambda_names'):
            raise DistutilsOptionError('lambda-names and/or function-names (DEPRECATED) is required')
        setattr(self, 'lambda_names', getattr(self, 'lambda_names') + ',' + getattr(self, 'function_names'))
        setattr(self, 'layer_runtimes', getattr(self, 'layer_runtimes').split(','))

    def run(self):
        """Run command."""
        self.run_command('lupload')
        ldist_cmd = self.get_finalized_command('ldist')
        lupload_cmd = self.get_finalized_command('lupload')
        s3_bucket = getattr(lupload_cmd, 's3_bucket')
        s3_key = getattr(lupload_cmd, 's3_object_key')
        s3_object_version = getattr(lupload_cmd, 's3_object_version')
        # s3_object_version could be None if Versioning is not enabled in that
        # bucket. That will be okay as it is optional to update_function_code.
        if s3_bucket is None or s3_key is None:
            raise DistutilsArgError('\'lupload\' missing attributes')
        aws_lambda = boto3.client(
            'lambda',
            config=Config(signature_version='s3v4'),
            region_name=getattr(self, 'region')
        )
        for lambda_name in set(getattr(self, 'lambda_names').split(',')):
            if not lambda_name:
                continue
            if not getattr(ldist_cmd, 'build_layer', False):
                try:
                    log.info('Updating and publishing function {}'.format(lambda_name))
                    kwargs = dict(
                        FunctionName=lambda_name,
                        S3Bucket=s3_bucket,
                        S3Key=s3_key,
                        Publish=True
                    )
                    if s3_object_version:
                        kwargs['S3ObjectVersion'] = s3_object_version
                    aws_lambda.update_function_code(**kwargs)
                except ClientError as err:
                    log.warn('Error updating function {}\n{}'.format(lambda_name, err))
            else:
                try:
                    log.info('Publishing layer {}'.format(lambda_name))
                    content = dict(S3Bucket = s3_bucket, S3Key = s3_key)
                    if s3_object_version:
                        content['S3ObjectVersion'] = s3_object_version
                    aws_lambda.publish_layer_version(
                        LayerName=lambda_name,
                        Description='{}-{}'.format(self.distribution.get_name(), self.distribution.get_version()),
                        Content=content,
                        CompatibleRuntimes=getattr(self, 'layer_runtimes')
                    )
                except ClientError as err:
                    log.warn('Error publishing layer {}\n{}'.format(lambda_name, err))
