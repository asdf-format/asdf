# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module provides the tools used to internally run the astropy test suite
from the installed astropy.  It makes use of the `pytest` testing framework.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six

import errno
import shlex
import sys
import multiprocessing
import os
import types
import warnings

__all__ = ['enable_deprecations_as_exceptions', 'remote_data',
           'treat_deprecations_as_exceptions', 'catch_warnings']

try:
    # Import pkg_resources to prevent it from issuing warnings upon being
    # imported from within py.test.  See
    # https://github.com/astropy/astropy/pull/537 for a detailed explanation.
    import pkg_resources
except ImportError:
    pass

from ... import test


import pytest


# Monkey-patch py.test to work around issue #811
# https://github.com/astropy/astropy/issues/811
from _pytest.assertion import rewrite as _rewrite
_orig_write_pyc = _rewrite._write_pyc


def _write_pyc_wrapper(*args):
    """Wraps the internal _write_pyc method in py.test to recognize
    PermissionErrors and just stop trying to cache its generated pyc files if
    it can't write them to the __pycache__ directory.

    When py.test scans for test modules, it actually rewrites the bytecode
    of each test module it discovers--this is how it manages to add extra
    instrumentation to the assert builtin.  Normally it caches these
    rewritten bytecode files--``_write_pyc()`` is just a function that handles
    writing the rewritten pyc file to the cache.  If it returns ``False`` for
    any reason py.test will stop trying to cache the files altogether.  The
    original function catches some cases, but it has a long-standing bug of
    not catching permission errors on the ``__pycache__`` directory in Python
    3.  Hence this patch.
    """

    try:
        return _orig_write_pyc(*args)
    except IOError as e:
        if e.errno == errno.EACCES:
            return False
_rewrite._write_pyc = _write_pyc_wrapper


# pytest marker to mark tests which get data from the web
remote_data = pytest.mark.remote_data


class TestRunner(object):
    def __init__(self, base_path):
        self.base_path = base_path

    def run_tests(self, package=None, test_path=None, args=None, plugins=None,
                  verbose=False, pastebin=None, remote_data=False, pep8=False,
                  pdb=False, coverage=False, open_files=False, parallel=0,
                  docs_path=None, skip_docs=False, repeat=None):
        """
        The docstring for this method lives in astropy/__init__.py:test
        """
        if coverage:
            warnings.warn(
                "The coverage option is ignored on run_tests, since it "
                "can not be made to work in that context.  Use "
                "'python setup.py test --coverage' instead.")

        all_args = []

        if package is None:
            package_path = self.base_path
        else:
            package_path = os.path.join(self.base_path,
                                        package.replace('.', os.path.sep))

            if not os.path.isdir(package_path):
                raise ValueError('Package not found: {0}'.format(package))

        if docs_path is not None and not skip_docs:
            if package is not None:
                docs_path = os.path.join(
                    docs_path, package.replace('.', os.path.sep))
            if not os.path.exists(docs_path):
                warnings.warn(
                    "Can not test .rst docs, since docs path "
                    "({0}) does not exist.".format(docs_path))
                docs_path = None

        if test_path:
            base, ext = os.path.splitext(test_path)

            if ext in ('.rst', ''):
                if docs_path is None:
                    # This shouldn't happen from "python setup.py test"
                    raise ValueError(
                        "Can not test .rst files without a docs_path "
                        "specified.")

                abs_docs_path = os.path.abspath(docs_path)
                abs_test_path = os.path.abspath(
                    os.path.join(abs_docs_path, os.pardir, test_path))

                common = os.path.commonprefix((abs_docs_path, abs_test_path))

                if os.path.exists(abs_test_path) and common == abs_docs_path:
                    # Since we aren't testing any Python files within
                    # the astropy tree, we need to forcibly load the
                    # astropy py.test plugins, and then turn on the
                    # doctest_rst plugin.
                    all_args.extend(['-p', 'astropy.tests.pytest_plugins',
                                     '--doctest-rst'])
                    test_path = abs_test_path

            if not (os.path.isdir(test_path) or ext in ('.py', '.rst')):
                raise ValueError("Test path must be a directory or a path to "
                                 "a .py or .rst file")

            all_args.append(test_path)
        else:
            all_args.append(package_path)
            if docs_path is not None and not skip_docs:
                all_args.extend([docs_path, '--doctest-rst'])

        # add any additional args entered by the user
        if args is not None:
            all_args.extend(
                shlex.split(args, posix=not sys.platform.startswith('win')))

        # add verbosity flag
        if verbose:
            all_args.append('-v')

        # turn on pastebin output
        if pastebin is not None:
            if pastebin in ['failed', 'all']:
                all_args.append('--pastebin={0}'.format(pastebin))
            else:
                raise ValueError("pastebin should be 'failed' or 'all'")

        # run @remote_data tests
        if remote_data:
            all_args.append('--remote-data')

        if pep8:
            try:
                import pytest_pep8
            except ImportError:
                raise ImportError('PEP8 checking requires pytest-pep8 plugin: '
                                  'http://pypi.python.org/pypi/pytest-pep8')
            else:
                all_args.extend(['--pep8', '-k', 'pep8'])

        # activate post-mortem PDB for failing tests
        if pdb:
            all_args.append('--pdb')

        # check for opened files after each test
        if open_files:
            if parallel != 0:
                raise SystemError(
                    "open file detection may not be used in conjunction with "
                    "parallel testing.")

            try:
                import psutil
            except ImportError:
                raise SystemError(
                    "open file detection requested, but psutil package "
                    "is not installed.")

            all_args.append('--open-files')

            print("Checking for unclosed files")

        if parallel != 0:
            try:
                import xdist
            except ImportError:
                raise ImportError(
                    'Parallel testing requires the pytest-xdist plugin '
                    'https://pypi.python.org/pypi/pytest-xdist')

            try:
                parallel = int(parallel)
            except ValueError:
                raise ValueError(
                    "parallel must be an int, got {0}".format(parallel))

            if parallel < 0:
                parallel = multiprocessing.cpu_count()
            all_args.extend(['-n', six.text_type(parallel)])

        if repeat:
            all_args.append('--repeat={0}'.format(repeat))

        if six.PY2:
            all_args = [x.encode('utf-8') for x in all_args]

        print(all_args)
        return pytest.main(args=all_args, plugins=plugins)

    run_tests.__doc__ = test.__doc__


# This is for Python 2.x and 3.x compatibility.  distutils expects
# options to all be byte strings on Python 2 and Unicode strings on
# Python 3.
def _fix_user_options(options):
    def to_str_or_none(x):
        if x is None:
            return None
        return str(x)

    return [tuple(to_str_or_none(x) for x in y) for y in options]


def _save_coverage(cov, result, rootdir, testing_path):
    """
    This method is called after the tests have been run in coverage mode
    to cleanup and then save the coverage data and report.
    """
    from ..utils.console import color_print

    if result != 0:
        return

    # The coverage report includes the full path to the temporary
    # directory, so we replace all the paths with the true source
    # path. This means that the coverage line-by-line report will only
    # be correct for Python 2 code (since the Python 3 code will be
    # different in the build directory from the source directory as
    # long as 2to3 is needed). Therefore we only do this fix for
    # Python 2.x.
    if six.PY2:
        d = cov.data
        cov._harvest_data()
        for key in d.lines.keys():
            new_path = os.path.relpath(
                os.path.realpath(key),
                os.path.realpath(testing_path))
            new_path = os.path.abspath(
                os.path.join(rootdir, new_path))
            d.lines[new_path] = d.lines.pop(key)

    color_print('Saving coverage data in .coverage...', 'green')
    cov.save()

    color_print('Saving HTML coverage report in htmlcov...', 'green')
    cov.html_report(directory=os.path.join(rootdir, 'htmlcov'))


_deprecations_as_exceptions = False
_include_astropy_deprecations = True

def enable_deprecations_as_exceptions(include_astropy_deprecations=True):
    """
    Turn on the feature that turns deprecations into exceptions.
    """

    global _deprecations_as_exceptions
    _deprecations_as_exceptions = True

    global _include_astropy_deprecations
    _include_astropy_deprecations = include_astropy_deprecations


def treat_deprecations_as_exceptions():
    """
    Turn all DeprecationWarnings (which indicate deprecated uses of
    Python itself or Numpy, but not within Astropy, where we use our
    own deprecation warning class) into exceptions so that we find
    out about them early.

    This completely resets the warning filters and any "already seen"
    warning state.
    """
    if not _deprecations_as_exceptions:
        return

    # First, totally reset the warning state
    for module in list(six.itervalues(sys.modules)):
        # We don't want to deal with six.MovedModules, only "real"
        # modules.
        if (isinstance(module, types.ModuleType) and
            hasattr(module, '__warningregistry__')):
            del module.__warningregistry__

    warnings.resetwarnings()

    # Hide the next couple of DeprecationWarnings
    warnings.simplefilter('ignore', DeprecationWarning)
    # Here's the wrinkle: a couple of our third-party dependencies
    # (py.test and scipy) are still using deprecated features
    # themselves, and we'd like to ignore those.  Fortunately, those
    # show up only at import time, so if we import those things *now*,
    # before we turn the warnings into exceptions, we're golden.
    try:
        # A deprecated stdlib module used by py.test
        import compiler
    except ImportError:
        pass

    # Now, start over again with the warning filters
    warnings.resetwarnings()
    # Now, turn DeprecationWarnings into exceptions
    warnings.filterwarnings("error", ".*", DeprecationWarning)

    if sys.version_info[:2] == (2, 6):
        # py.test's warning.showwarning does not include the line argument
        # on Python 2.6, so we need to explicitly ignore this warning.
        warnings.filterwarnings(
            "always",
            r"functions overriding warnings\.showwarning\(\) must support "
            r"the 'line' argument",
            DeprecationWarning)

    if sys.version_info[:2] >= (3, 4):
        # py.test reads files with the 'U' flag, which is now
        # deprecated in Python 3.4.
        warnings.filterwarnings(
            "always",
            r"'U' mode is deprecated",
            DeprecationWarning)

        # BeautifulSoup4 triggers a DeprecationWarning in stdlib's
        # html module.x
        warnings.filterwarnings(
            "always",
            "The strict argument and mode are deprecated.",
            DeprecationWarning)
        warnings.filterwarnings(
            "always",
            "The value of convert_charrefs will become True in 3.5. "
            "You are encouraged to set the value explicitly.",
            DeprecationWarning)


class catch_warnings(warnings.catch_warnings):
    """
    A high-powered version of warnings.catch_warnings to use for testing
    and to make sure that there is no dependence on the order in which
    the tests are run.

    This completely blitzes any memory of any warnings that have
    appeared before so that all warnings will be caught and displayed.

    ``*args`` is a set of warning classes to collect.  If no arguments are
    provided, all warnings are collected.

    Use as follows::

        with catch_warnings(MyCustomWarning) as w:
            do.something.bad()
        assert len(w) > 0
    """
    def __init__(self, *classes):
        super(catch_warnings, self).__init__(record=True)
        self.classes = classes

    def __enter__(self):
        warning_list = super(catch_warnings, self).__enter__()
        treat_deprecations_as_exceptions()
        if len(self.classes) == 0:
            warnings.simplefilter('always')
        else:
            warnings.simplefilter('ignore')
            for cls in self.classes:
                warnings.simplefilter('always', cls)
        return warning_list

    def __exit__(self, type, value, traceback):
        treat_deprecations_as_exceptions()
