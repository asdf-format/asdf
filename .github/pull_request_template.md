## Description
<!--
Thanks for contributing to asdf!

Please describe what this PR accomplishes.
If the changes are non-obvious, please explain how they work.
If this PR adds a new feature please include tests and documentation.
If this PR fixes an issue, please add closing keywords (eg 'fixes #XXX')
-->

## AI Disclosure
<!--
If AI tools were used as part of development of this pull request, please describe which tools and the extent of their use.
If no AI tools were used, please write "No AI tools used".

All AI usage must comply with our AI policy:
https://github.com/asdf-format/.github/blob/main/AI_POLICY.md
-->

## Tasks

- [ ] [run `prek` on your machine](https://prek.j178.dev/quickstart/)
- [ ] [run `pytest` on your machine](https://docs.pytest.org/en/7.1.x/getting-started.html)
- [ ] Does this PR add new features and / or change user-facing code / API? (if not, label with `no-changelog-entry-needed`)
    - [ ] write news fragment(s) in `changes/`: `echo "changed something" > changes/<PR#>.<changetype>.md` (see below for change types)
    - [ ] update relevant docstrings and / or `docs/` page
    - [ ] for any new features, add unit tests

<details><summary>news fragment change types...</summary>

- ``changes/<PR#>.feature.md``: new feature
- ``changes/<PR#>.bugfix.md``: bug fix
- ``changes/<PR#>.doc.md``: documentation change
- ``changes/<PR#>.removal.md``: deprecation or removal of public API
- ``changes/<PR#>.general.md``: infrastructure or miscellaneous change
</details>
