# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function

import os
import shutil

import pytest
import vistir

import requirementslib.utils


def check_for_mercurial():
    c = vistir.misc.run(["hg, --help"], return_object=True, block=True, nospin=True,
                        combine_stderr=False)
    if c.returncode != 0:
        return False
    else:
        return True


HAS_MERCURIAL = check_for_mercurial()


def pytest_runtest_setup(item):
    if item.get_marker('needs_hg') is not None and not HAS_MERCURIAL:
        pytest.skip('requires mercurial')


@pytest.fixture
def pathlib_tmpdir(tmpdir):
    yield vistir.compat.Path(str(tmpdir))
    try:
        tmpdir.remove(ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def pip_src_dir(request, pathlib_tmpdir):
    old_src_dir = os.environ.get('PIP_SRC', '')
    os.environ['PIP_SRC'] = pathlib_tmpdir.as_posix()

    def finalize():
        os.environ['PIP_SRC'] = vistir.compat.fs_str(old_src_dir)

    request.addfinalizer(finalize)
    return request


@pytest.fixture(scope="session")
def artifact_dir():
    return vistir.compat.Path(
        requirementslib.utils.__file__
    ).absolute().parent.parent.parent.joinpath("tests/artifacts")


@pytest.fixture
def test_artifact(artifact_dir, pathlib_tmpdir, request):
    name = request.param["name"]
    as_artifact = request.param.get("as_artifact", False)
    target = artifact_dir.joinpath(name)
    if target.exists():
        if as_artifact:
            files = [path for path in target.iterdir() if path.is_file()]
        else:
            files = [path for path in target.iterdir() if path.is_dir()]
        files = sorted(files, reverse=True)
        installable_files = [
            f for f in files if requirementslib.utils.is_installable_file(f.as_posix()) or
            f.joinpath("setup.py").exists() or
            f.joinpath("pyproject.toml").exists() or
            f.joinpath("setup.cfg").exists()
        ]
        installable = next(iter(f for f in installable_files), None)
        if installable:
            target_path = pathlib_tmpdir.joinpath(installable.name)
            if as_artifact:
                shutil.copy(installable.as_posix(), target_path.as_posix())
            else:
                shutil.copytree(installable.as_posix(), target_path.as_posix())
            yield target_path
            if as_artifact:
                target_path.unlink()
        else:
            raise RuntimeError(
                "failed to find installable artifact: %s (as_artifact: %s)\n"
                "files: %s\nInstallable: %s" % (name, as_artifact, files, installable)
            )
