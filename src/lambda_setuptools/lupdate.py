import boto3
import json

from botocore.client import Config
from botocore.exceptions import ClientError
from distutils import log
from distutils.errors import DistutilsArgError, DistutilsOptionError
from setuptools import Command


class LUpdate(Command):
    description = 'Update the specified Lambda functions with the result of the lupload command'
    user_options = [
        ('function-names=', None, 'Comma seperated list of function names to update. Must have at least one entry. Can be functon name, partial ARNs, and/or full ARNs'),
        ('region=', None, 'Region for the named lambda functions. Defaults to "us-east-1"')
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        setattr(self, 'function_names', None)
        setattr(self, 'region', 'us-east-1')

    def finalize_options(self):
        """Post-process options."""
        if getattr(self, 'function_names') is None:
            raise DistutilsOptionError('function-names is required')

    def run(self):
        """Run command."""
        self.run_command('lupload')
        lupload_cmd = self.get_finalized_command('lupload')
        s3_bucket = getattr(lupload_cmd, 's3_bucket')
        s3_key = getattr(lupload_cmd, 's3_object_key')
        s3_object_version = getattr(lupload_cmd, 's3_object_version')
        if s3_bucket is None or s3_key is None or s3_object_version is None:
            raise DistutilsArgError('\'lupload\' missing attributes')
        aws_lambda = boto3.client(
            'lambda',
            aws_access_key_id=getattr(lupload_cmd, 'access_key'),
            aws_secret_access_key=getattr(lupload_cmd, 'secret_access_key'),
            config=Config(signature_version='s3v4'),
            region_name=getattr(self, 'region')
        )
        for function_name in getattr(self, 'function_names').split(','):
            try:
                log.info('Updating and publishing {}'.format(function_name))
                aws_lambda.update_function_code(
                    FunctionName=function_name,
                    S3Bucket=s3_bucket,
                    S3Key=s3_key,
                    S3ObjectVersion=s3_object_version,
                    Publish=True
                )
            except ClientError as err:
                log.warn('Error updating {}\n{}'.format(function_name, err))
