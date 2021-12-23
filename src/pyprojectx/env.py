"""
Creates and manages isolated build environments.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

import virtualenv

from pyprojectx.log import logger


def _calculate_path(base_path: Path, name: str, requirements: Iterable[str]) -> Path:
    md5 = hashlib.md5()
    for req in requirements:
        md5.update(req.strip().encode())
    return Path(
        base_path, f"{name.lower()}-{md5.hexdigest()}-py{sys.version_info.major}.{sys.version_info.minor}"
    ).absolute()


class IsolatedVirtualEnv:
    """
    Encapsulates the location and installation of an isolated virtual environment.
    """

    def __init__(self, base_path: Path, name: str, requirements: Iterable[str]) -> None:
        """
        :param base_path: The base path for all environments
        :param name: The name for the environment
        :param requirements: The requirements to install in the environment
        """
        self._base_path = base_path
        self._requirements = requirements
        self._path = _calculate_path(base_path, name, self._requirements)
        self._scripts_path_file = self._path.joinpath(".scripts_path")
        self._executable = None

    @property
    def path(self) -> Path:
        """
        The location of the isolated environment.
        """
        return self._path

    @property
    def executable(self) -> Optional[Path]:
        """
        The location of the Python executable of the isolated environment.
        """
        return self._executable

    @property
    def scripts_path(self) -> Optional[Path]:
        """
        The location of the scripts directory.
        """
        if self._scripts_path_file.exists():
            with open(self._scripts_path_file, "r") as sf:
                return Path(sf.readline())
        return None

    @property
    def is_installed(self) -> bool:
        return self.scripts_path and self.scripts_path.is_dir()

    def install(self, quiet=False) -> None:
        """
        Create the virtual environment and install requirements
        """
        logger.debug("Installing IsolatedVirtualEnv in %s", self.path)
        scripts_dir = self._create_virtual_env()
        self._install_requirements(quiet)
        with open(self._scripts_path_file, "w") as sf:
            sf.write(str(scripts_dir))

    def _create_virtual_env(self) -> Path:
        cmd = [str(self.path), "--no-setuptools", "--no-wheel", "--activators", ""]
        logger.debug("Calling virtualenv.cli_run: %s", " ".join(cmd))
        result = virtualenv.cli_run(cmd, setup_logging=False)
        scripts_dir = result.creator.script_dir
        self._executable = result.creator.exe
        return scripts_dir

    def _install_requirements(self, quiet=False):
        logger.info("Installing packages in isolated environment... (%s)", ", ".join(sorted(self._requirements)))
        # pip does not honour environment markers in command line arguments
        # but it does for requirements from a file
        with tempfile.NamedTemporaryFile("w+", prefix="build-reqs-", suffix=".txt", delete=False) as req_file:
            req_file.write(os.linesep.join(self._requirements))
        try:
            cmd = [
                self._executable,
                "-Im",
                "pip",
                "install",
            ]
            if quiet:
                cmd.append("--quiet")
            cmd += [
                "--use-pep517",
                "--no-warn-script-location",
                "-r",
                os.path.abspath(req_file.name),
            ]
            subprocess.run(
                cmd,
                stdout=sys.stderr,
                check=True,
            )
        finally:
            os.remove(req_file.name)

    def remove(self):
        """
        Remove the entire virtual environment
        """
        logger.info("Removing isolated environment in %s", self.path)
        shutil.rmtree(self.path)

    def run(self, cmd: Union[str, List[str]]) -> subprocess.CompletedProcess:
        """
        Run a command inside the virual environment.
        :param cmd: The command string to run
        :return: The subprocess.CompletedProcess instance
        """
        logger.info("Running command in IsolatedVirtualEnv: %s", cmd)
        paths: Dict[str, None] = OrderedDict()
        paths[str(self.scripts_path)] = None
        if "PATH" in os.environ:
            paths.update((i, None) for i in os.environ["PATH"].split(os.pathsep))
        extra_environ = {"PATH": os.pathsep.join(paths)}
        env = os.environ.copy()
        env.update(extra_environ)
        logger.debug("Environment for running command: %s", env)
        return subprocess.run(cmd, env=env, shell=isinstance(cmd, str), check=True)
