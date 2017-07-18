import errno
import os
import re
import shutil
import string
import zipfile

from distutils import log
from distutils.errors import DistutilsPlatformError, DistutilsInternalError, DistutilsSetupError
from setuptools import Command
from subprocess import Popen, PIPE


def validate_lambda_function(dist, attr, value):
    if not re.compile('^([a-zA-Z0-9_]+\.)*[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$').match(value):
        raise DistutilsSetupError('{} must be in the form of \'my_package.some_module:some_function\''.format(attr))


def add_lambda_module_to_py_modules(dist, attr, value):
    py_modules = getattr(dist, 'py_modules', None)
    if not py_modules:
        py_modules = []
    py_modules.append(value)
    setattr(dist, 'py_modules', py_modules)


def validate_lambda_package(dist, attr, value):
    if not os.path.exists(value) or not os.path.isdir(value):
        raise DistutilsSetupError('lambda_package either doesn\'t exist or is not a directory')
    if os.path.exists(os.path.join(value, '__init__.py')):
        raise DistutilsSetupError('{} {} cannot contain an __init__.py'.format(attr, value))


class LDist(Command):

    description = 'build a AWS Lambda compatible distribution'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        # We must create a distribution to install first
        # This is a short-cut to working with the actual build
        # directory, or to using the 'install' command, which
        # will generally only install a zipped egg
        self.run_command('bdist_wheel')
        setattr(self, '_dist_dir', self.get_finalized_command('bdist_wheel').dist_dir)

        # Install the package built by bdist_wheel
        # (or bdist, or bdist_wheel, depending on how the user called setup.py
        self._install_dist_package()

        # Use zero (if none specified) or more of the lambda_function, lambda_module or
        # lambda_package attributes to create the lambda entry point function
        self._create_lambda_entry_point()

        # Now build the lambda package
        self._build_lambda_package()

    def _build_lambda_package(self):
        dist_name = '{}-{}.zip'.format(self.distribution.get_name(), self.distribution.get_version())
        dist_path = os.path.join(self._dist_dir, dist_name)
        if os.path.exists(dist_path):
            os.remove(dist_path)
        log.info('creating {}'.format(dist_path))
        with zipfile.ZipFile(dist_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            abs_src = os.path.abspath(self._lambda_build_dir)
            for root, _, files in os.walk(self._lambda_build_dir):
                for filename in files:
                    absname = os.path.abspath(os.path.join(root, filename))
                    arcname = absname[len(abs_src) + 1:]
                    log.debug('zipping {} as {}'.format(os.path.join(root, filename), arcname))
                    zf.write(absname, arcname)
        # Set the resulting distribution file path for downstream command use
        setattr(self, 'dist_name', dist_name)
        setattr(self, 'dist_path', dist_path)

    def _create_lambda_entry_point(self):
        self._create_lambda_function()
        self._copy_lambda_package()

    def _create_lambda_function(self):
        lambda_function = getattr(self.distribution, 'lambda_function', None)
        if not lambda_function:
            return
        components = string.split(lambda_function, ':')
        module = components[0]
        function = components[1]
        function_lines = [
            'import {}\n'.format(module),
            '\n',
            '\n',
            'handler = {}.{}\n'.format(module, function)
        ]
        package_name = self.distribution.get_name().replace('-', '_').replace('.', '_')
        function_path = os.path.join(self._lambda_build_dir, '{}_function.py'.format(package_name))
        log.info('creating {}'.format(function_path))
        with open(function_path, 'w') as py:
            py.writelines(function_lines)

    def _copy_lambda_package(self):
        lambda_package = getattr(self.distribution, 'lambda_package', None)
        if not lambda_package:
            return
        for filename in os.listdir(lambda_package):
            filepath = os.path.join(lambda_package, filename)
            if os.path.isdir(filepath):
                log.debug('{} is a directory, skipping lambda copy'.format(filepath))
                continue
            log.info('copying {} to {}'.format(filepath, self._lambda_build_dir))
            shutil.copy(filepath, self._lambda_build_dir)


    def _install_dist_package(self):
        # Get the name of the package that we just built
        package_name = self.distribution.get_name()
        # Get the dist directory that bdist_wheel put the package in
        # Create the lambda build dir
        self._lambda_build_dir = os.path.join('build', 'ldist-'+package_name)
        try:
            if os.path.exists(self._lambda_build_dir):
                shutil.rmtree(self._lambda_build_dir)
            log.info('creating {}'.format(self._lambda_build_dir))
            os.makedirs(self._lambda_build_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(self._lambda_build_dir):
                pass
            else:
                raise DistutilsInternalError('{} already exists and is not a directory'.format(self._lambda_build_dir))
        log.info('installing package {} from {} into {}'.format(package_name,
                                                                self._dist_dir,
                                                                self._lambda_build_dir))
        pip = Popen(['pip', 'install',
                     '-f', self._dist_dir,
                     '-t', self._lambda_build_dir, package_name],
                    stdout=PIPE, stderr=PIPE)
        stdout, stderr = pip.communicate()
        log.debug("pip stdout: {}".format(stdout))
        log.debug("pip stderr: {}".format(stderr))

        if pip.returncode is not 0:
            raise DistutilsPlatformError('pip returned unsuccessfully')
