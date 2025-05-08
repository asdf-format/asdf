We welcome feedback and contributions of all kinds. Contributions of code,
documentation, or general feedback are all appreciated. This package follows
the ASDF-format :ref:`Code Of Conduct <code-of-conduct>` and strives to provide a
welcoming community to all of our users and contributors.

New to GitHub or open source projects? If you are unsure about where to start or
haven't used GitHub before, please feel free to contact the package maintainers.

.. note::
    The ASDF Standard itself also has a repository on github. Suggestions for
    improvements to the ASDF Standard can be `reported to the ASDF Standard
    repository <https://github.com/asdf-format/asdf-standard/issues>`_.

Feedback, Feature Requests, and Bug Reports
-------------------------------------------

Feedback, feature requests, and bug reports for the ASDF Python implementation
can be posted via `ASDF's github page <https://github.com/asdf-format/asdf>`_.
Please open a new issue any questions, bugs, feedback, or new features you would
like to see. If there is an issue you would like to work on, please leave a comment
and we will be happy to assist. New contributions and contributors are very welcome!

Contributing Code and Bug Fixes
-------------------------------

To contribute code to ASDF please fork ASDF first and then open a pull request
from your fork to ASDF. Typically, the main development work is done on the
"main" branch.  The rest of the branches are for release maintenance and should
not be used normally. Unless otherwise told by a maintainer, pull request should
be made and submitted to the "main" branch.

.. note::
    The "stable" branch is protected and used for official releases.

We ask that all contributions include unit tests to verify that the code works as
intended. These tests are run automatically by GitHub when pull requests are open.
If you have difficulties with tests failing or writing new tests please reach out
to the maintainers, who are glad to assist you.

.. note::
    ASDF uses both ``black`` and ``ruff`` to format your code, so we ask that
    you run these tools regularly on your code to ensure that it is formatted
    correctly.

    To make this easier, we have included `pre-commit <https://pre-commit.com/>`__
    support for ASDF. We suggest that you install ``pre-commit``, so that your
    code is automatically formatted before you commit. For those who do not run
    these tools regularly, the ``pre-commit-ci`` bot will attempt to fix the issues
    with your pull request when you submit it.

.. note::
    Backporting changes is done automatically using ``meeseeksdev``. If you are
    a maintainer, you can comment ``@meeseeksdev backport to <branch>`` on a pull
    request to manually trigger a backport. Moreover, when merging a "backport"
    pull request, please use the "Rebase and merge" option.

.. note::
    When making a public change, add a news fragment to ``changes/`` with the
    filename ``<PR#>.<changetype>.rst``. The change types are as follows:

    - ``feature``: new feature
    - ``bugfix``: bug fix
    - ``doc``: documentation change
    - ``removal``: deprecation or removal of public API
    - ``general``: infrastructure or miscellaneous change
