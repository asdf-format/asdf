# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


__all__ = ['__version__', '__githash__', 'test']


try:
    from .version import version as __version__
except ImportError:
    __version__ = ''
try:
    from .version import githash as __githash__
except ImportError:
    __githash__ = ''


# set up the test command
def _get_test_runner():
    import os
    from astropy.tests.helper import TestRunner
    return TestRunner(os.path.dirname(__file__))


def test(package=None, test_path=None, args=None, plugins=None,
         verbose=False, pastebin=None, remote_data=False, pep8=False,
         pdb=False, coverage=False, open_files=False, **kwargs):
    """
    Run the tests using `pytest <http://pytest.org/latest>`__. A proper set
    of arguments is constructed and passed to `pytest.main`_.

    .. _pytest: http://pytest.org/latest/
    .. _pytest.main: http://pytest.org/latest/builtin.html#pytest.main

    Parameters
    ----------
    package : str, optional
        The name of a specific package to test, e.g. 'asdf.tags'.
        If nothing is specified all default tests are run.

    test_path : str, optional
        Specify location to test by path. May be a single file or
        directory. Must be specified absolutely or relative to the
        calling directory.

    args : str, optional
        Additional arguments to be passed to pytest.main_ in the ``args``
        keyword argument.

    plugins : list, optional
        Plugins to be passed to pytest.main_ in the ``plugins`` keyword
        argument.

    verbose : bool, optional
        Convenience option to turn on verbose output from pytest_. Passing
        True is the same as specifying ``'-v'`` in ``args``.

    pastebin : {'failed','all',None}, optional
        Convenience option for turning on pytest_ pastebin output. Set to
        ``'failed'`` to upload info for failed tests, or ``'all'`` to upload
        info for all tests.

    remote_data : bool, optional
        Controls whether to run tests marked with @remote_data. These
        tests use online data and are not run by default. Set to True to
        run these tests.

    pep8 : bool, optional
        Turn on PEP8 checking via the `pytest-pep8 plugin
        <http://pypi.python.org/pypi/pytest-pep8>`_ and disable normal
        tests. Same as specifying ``'--pep8 -k pep8'`` in ``args``.

    pdb : bool, optional
        Turn on PDB post-mortem analysis for failing tests. Same as
        specifying ``'--pdb'`` in ``args``.

    coverage : bool, optional
        Generate a test coverage report.  The result will be placed in
        the directory htmlcov.

    open_files : bool, optional
        Fail when any tests leave files open.  Off by default, because
        this adds extra run time to the test suite.  Requires the
        `psutil <https://pypi.python.org/pypi/psutil>`_ package.

    parallel : int, optional
        When provided, run the tests in parallel on the specified
        number of CPUs.  If parallel is negative, it will use the all
        the cores on the machine.  Requires the
        `pytest-xdist <https://pypi.python.org/pypi/pytest-xdist>`_ plugin
        installed.

    kwargs
        Any additional keywords passed into this function will be passed
        on to the astropy test runner.  This allows use of test-related
        functionality implemented in later versions of astropy without
        explicitly updating the package template.

    """

    test_runner = _get_test_runner()
    return test_runner.run_tests(
        package=package, test_path=test_path, args=args,
        plugins=plugins, verbose=verbose, pastebin=pastebin,
        remote_data=remote_data, pep8=pep8, pdb=pdb,
        coverage=coverage, open_files=open_files, **kwargs)
