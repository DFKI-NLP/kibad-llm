## documentation

- all python files need to be documented at the file level
- all python classes, functions, and methods are required to carry a docstring
- all docstrings must be fully markdown compatible in the dialect CommonMark (for use with the static docs provided by properdocs)
    - all markdown files must also be compatible with the github markdown dialect
    - do not use sphinx/rst syntax, but markdown only
- if you need to take notes, do so in NOTES.md. do not ever commit that file.

## project quality

to ensure basic quality automatically, the cicd pipeline with prek must pass without errors.

additionally, code should have tests. the test must pass for a pr to be merged. slow tests must be marked as such and be tested separately. the cicd pipeline doesn't run slow tests, but they are a requirement for prs to be merged.
