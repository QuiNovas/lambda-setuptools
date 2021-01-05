import errno
import os
import re
import shutil
import zipfile
from distutils import log
from distutils.errors import (
    DistutilsInternalError,
    DistutilsOptionError,
    DistutilsSetupError,
)

from lambda_pkg_resources import LAMBDA_EXCLUDES, DistInstaller, ExcludesWorkingSet
from pkg_resources import WorkingSet, parse_requirements
from setuptools import Command


def validate_lambda_function(dist, attr, value):
    if not re.compile(r"^([a-zA-Z0-9_]+\.)*[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$").match(value):
        raise DistutilsSetupError(
            f"{attr} must be in the form of 'my_package.some_module:some_function'"
        )


def add_lambda_module_to_py_modules(dist, attr, value):
    py_modules = getattr(dist, "py_modules", None)
    if not py_modules:
        py_modules = []
    py_modules.append(value)
    setattr(dist, "py_modules", py_modules)


def validate_lambda_package(dist, attr, value):
    if not os.path.exists(value) or not os.path.isdir(value):
        raise DistutilsSetupError(
            "lambda_package either doesn't exist or is not a directory"
        )
    if os.path.exists(os.path.join(value, "__init__.py")):
        raise DistutilsSetupError(f"{attr} {value} cannot contain an __init__.py")


class LDist(Command):

    description = "build a AWS Lambda compatible distribution"
    user_options = [
        (
            "exclude-lambda-packages=",
            None,
            "Excludes the packages that are provided by the AWS Lambda execution environment",
        ),
        (
            "include-version=",
            None,
            "Include the version number on the lambda distribution name",
        ),
        ("build-layer=", None, "Build a layer instead of a function distribution"),
        (
            "layer-dir=",
            None,
            'The directory to place the layer into. Defaults to "python" if not provided',
        ),
    ]

    def initialize_options(self):
        """Set default values for options."""
        # Each user option must be listed here with their default value.
        setattr(self, "exclude_lambda_packages", None)
        setattr(self, "include_version", None)
        setattr(self, "build_layer", None)
        setattr(self, "layer_dir", None)

    def finalize_options(self):
        exclude_lambda_packages = getattr(self, "exclude_lambda_packages")
        if (
            exclude_lambda_packages is None
            or exclude_lambda_packages == ""
            or exclude_lambda_packages == "True"
            or exclude_lambda_packages == "true"
            or exclude_lambda_packages == "Yes"
            or exclude_lambda_packages == "yes"
        ):
            setattr(self, "exclude_lambda_packages", True)
        elif (
            exclude_lambda_packages == "False"
            or exclude_lambda_packages == "false"
            or exclude_lambda_packages == "No"
            or exclude_lambda_packages == "no"
        ):
            setattr(self, "exclude_lambda_packages", False)
        else:
            raise DistutilsOptionError(
                "exclude-lambda-packages must be True, true, Yes, yes, False, false, No, no or absent"
            )
        include_version = getattr(self, "include_version")
        if (
            include_version is None
            or include_version == ""
            or include_version == "True"
            or include_version == "true"
            or include_version == "Yes"
            or include_version == "yes"
        ):
            setattr(self, "include_version", True)
        elif (
            include_version == "False"
            or include_version == "false"
            or include_version == "No"
            or include_version == "no"
        ):
            setattr(self, "include_version", False)
        else:
            raise DistutilsOptionError(
                "include-version must be True, true, Yes, yes, False, false, No, no or absent"
            )
        build_layer = getattr(self, "build_layer")
        if (
            build_layer == "True"
            or build_layer == "true"
            or build_layer == "Yes"
            or build_layer == "yes"
        ):
            setattr(self, "build_layer", True)
        elif (
            build_layer is None
            or build_layer == ""
            or build_layer == "False"
            or build_layer == "false"
            or build_layer == "No"
            or build_layer == "no"
        ):
            setattr(self, "build_layer", False)
        else:
            raise DistutilsOptionError(
                "build-layer must be True, true, Yes, yes, False, false, No, no or absent"
            )
        layer_dir = getattr(self, "layer_dir")
        if layer_dir is None:
            setattr(self, "layer_dir", "python")

    def run(self):
        # We must create a distribution to install first
        # This is a short-cut to working with the actual build
        # directory, or to using the 'install' command, which
        # will generally only install a zipped egg
        self.run_command("bdist_wheel")
        bdist_wheel_command = self.get_finalized_command("bdist_wheel")
        setattr(self, "_dist_dir", bdist_wheel_command.dist_dir)

        # Install the package built by bdist_wheel
        # (or bdist, or bdist_wheel, depending on how the user called setup.py
        impl_tag, abi_tag, plat_tag = bdist_wheel_command.get_tag()
        self._install_dist_package(
            os.path.join(
                bdist_wheel_command.dist_dir,
                f"{bdist_wheel_command.wheel_dist_name}-{impl_tag}-{abi_tag}-{plat_tag}.whl",
            )
        )

        # Use zero (if none specified) or more of the lambda_function, lambda_module or
        # lambda_package attributes to create the lambda entry point function
        if not getattr(self, "build_layer"):
            self._create_lambda_entry_point()

        # Now build the lambda package
        self._build_lambda_package()

    def _build_lambda_package(self):
        dist_name = (
            f"{self.distribution.get_name()}-{self.distribution.get_version()}.zip"
            if getattr(self, "include_version")
            else f"{self.distribution.get_name()}.zip"
        )
        dist_path = os.path.join(self._dist_dir, dist_name)
        if os.path.exists(dist_path):
            os.remove(dist_path)
        log.info(f"creating {dist_path}")
        with zipfile.ZipFile(dist_path, "w", zipfile.ZIP_DEFLATED) as zf:
            abs_src = os.path.abspath(self._lambda_build_dir)
            for root, _, files in os.walk(self._lambda_build_dir):
                for filename in files:
                    absname = os.path.abspath(os.path.join(root, filename))
                    arcname = absname[len(abs_src) + 1 :]
                    log.debug(f"zipping {os.path.join(root, filename)} as {arcname}")
                    zf.write(absname, arcname)
        # Set the resulting distribution file path for downstream command use
        setattr(self, "dist_name", dist_name)
        setattr(self, "dist_path", dist_path)

    def _create_lambda_entry_point(self):
        self._create_lambda_function()
        self._copy_lambda_package()

    def _create_lambda_function(self):
        lambda_function = getattr(self.distribution, "lambda_function", None)
        if not lambda_function:
            return
        components = lambda_function.split(":")
        module = components[0]
        function = components[1]
        function_lines = [
            f"import {module}\n",
            "\n",
            "\n",
            f"handler = {module}.{function}\n",
        ]
        package_name = self.distribution.get_name().replace("-", "_").replace(".", "_")
        function_path = os.path.join(
            self._lambda_build_dir, f"{package_name}_function.py"
        )
        log.info(f"creating {function_path}")
        with open(function_path, "w") as py:
            py.writelines(function_lines)

    def _copy_lambda_package(self):
        lambda_package = getattr(self.distribution, "lambda_package", None)
        if not lambda_package:
            return
        for filename in os.listdir(lambda_package):
            filepath = os.path.join(lambda_package, filename)
            if os.path.isdir(filepath):
                log.debug(f"{filepath} is a directory, skipping lambda copy")
                continue
            log.info(f"copying {filepath} to {self._lambda_build_dir}")
            shutil.copy(filepath, self._lambda_build_dir)

    def _install_dist_package(self, wheel_path):
        # Get the name of the package that we just built
        package_name = self.distribution.get_name()
        # Get the dist directory that bdist_wheel put the package in
        # Create the lambda build dir
        self._lambda_build_dir = os.path.join("build", "ldist-" + package_name)
        build_dir = self._lambda_build_dir
        if getattr(self, "build_layer"):
            build_dir = os.path.join(build_dir, getattr(self, "layer_dir"))
        try:
            if os.path.exists(self._lambda_build_dir):
                shutil.rmtree(self._lambda_build_dir)
            log.info(f"creating {self._lambda_build_dir}")
            os.makedirs(build_dir)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(self._lambda_build_dir):
                pass
            else:
                raise DistutilsInternalError(
                    f"{self._lambda_build_dir} already exists and is not a directory"
                )
        log.info(
            f"installing package {package_name} from {self._dist_dir} into {build_dir}"
        )
        # Extract our wheel into our build dir
        with zipfile.ZipFile(wheel_path, "r") as zf:
            zf.extractall(build_dir)

        # Create the working set to get all recursive dependencies, EXCEPT for the libraries included
        # with the lambda environment
        working_set = (
            ExcludesWorkingSet(entries=[build_dir], excludes=LAMBDA_EXCLUDES)
            if getattr(self, "exclude_lambda_packages")
            else WorkingSet(entries=[build_dir])
        )
        dist_installer = DistInstaller(build_dir)
        working_set.resolve(
            parse_requirements(package_name),
            installer=dist_installer.fetch_dist,
            replace_conflicting=True,
        )
