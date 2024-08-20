<!---
Thanks for contributing to asdf!

Your PR should trigger the CI (after approval for first-time contributors)
which will:

- check your code for 'style' using pre-commit
- run your PR against the asdf unit tests for various OSes, python versions, and dependency versions
- perform a test build of your PR

It is highly recommended that you run some of these tests locally by:

- [installing pre-commit](https://pre-commit.com/#quick-start)
- [running pytest](https://docs.pytest.org/en/7.1.x/getting-started.html)

This will increase the chances your PR will pass the required CI tests.
-->

# Description

<!--
Please describe what this PR accomplishes.
If the changes are non-obvious, please explain how they work.
If this PR adds a new feature please include tests and documentation.
If this PR fixes an issue, please add closing keywords (eg 'fixes #XXX')
-->

# Checklist:

- [ ] pre-commit checks ran successfully
- [ ] tests ran successfully
- [ ] for a public change, added a [towncrier news fragment](https://towncrier.readthedocs.io/en/stable/tutorial.html#creating-news-fragments) <details><summary>`changes/<PR#>.<changetype>.rst`</summary>

    - ``changes/<PR#>.feature.rst``: new feature
    - ``changes/<PR#>.bugfix.rst``: bug fix
    - ``changes/<PR#>.doc.rst``: documentation change
    - ``changes/<PR#>.removal.rst``: deprecation or removal of public API
    - ``changes/<PR#>.misc.rst``: not of interest to users; use an empty file
  </details>
- [ ] for a public change, updated documentation
- [ ] for any new features, unit tests were added
