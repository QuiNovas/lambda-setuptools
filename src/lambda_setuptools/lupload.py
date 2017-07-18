import boto3
import json

from botocore.client import Config
from distutils import log
from distutils.errors import DistutilsArgError, DistutilsOptionError
from setuptools import Command


class LUpload(Command):
    description = 'upload the result of the ldist command to S3'
    user_options = [
        # The format is (long option, short option, description).
        ('access-key=', None, 'The access key to use to upload'),
        ('s3-prefix=', None, 'The prefix to use when uploading the dist (optional)'),
        ('kms-key-id=', None, 'The KMS key to use on upload (optional, but recommended)'),
        ('secret-access-key=', None, 'The secret access to use to upload'),
        ('s3-bucket=', None, 'The bucket to upload to')
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        setattr(self, 'access_key', None)
        setattr(self, 'kms_key_id', None)
        setattr(self, 's3_prefix', '')
        setattr(self, 'secret_access_key', None)
        setattr(self, 's3_bucket', None)

    def finalize_options(self):
        """Post-process options."""
        if getattr(self, 'access_key') is None or \
                        getattr(self, 'secret_access_key') is None or \
                        getattr(self, 's3_bucket') is None:
            raise DistutilsOptionError('access-key, secret-access-key, s3-bucket are required')

    def run(self):
        """Run command."""
        self.run_command('ldist')
        ldist_cmd = self.get_finalized_command('ldist')
        dist_path = getattr(ldist_cmd, 'dist_path', None)
        dist_name = getattr(ldist_cmd, 'dist_name', None)
        if dist_path is None or dist_name is None:
            raise DistutilsArgError('\'ldist\' missing attributes')
        dist_name = getattr(self, 's3_prefix') + dist_name
        s3 = boto3.client(
            's3',
            aws_access_key_id=getattr(self, 'access_key'),
            aws_secret_access_key=getattr(self, 'secret_access_key'),
            config=Config(signature_version='s3v4')
        )
        log.info('uploading {} to {} using kms key {}'.format(
            dist_name,
            getattr(self, 's3_bucket'),
            getattr(self, 'kms_key_id')
        ))
        with open(dist_path) as dist:
            if getattr(self, 'kms_key_id'):
                response = s3.put_object(
                    Body=dist,
                    Bucket=getattr(self, 's3_bucket'),
                    Key=dist_name,
                    ServerSideEncryption='aws:kms',
                    SSEKMSKeyId=getattr(self, 'kms_key_id')
                )
            else:
                response = s3.put_object(
                    Body=dist,
                    Bucket=getattr(self, 's3_bucket'),
                    Key=dist_name,
                    ServerSideEncryption='AES256'
                )
        log.info('upload complete:\n{}'.format(
            json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
        )
