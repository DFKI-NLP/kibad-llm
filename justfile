
# The first recipe is the default one, if just is run without a specific recipe `$ just`
default: pr

# SERVING

# locally serve the docs
prop:
    uv run --group cicd properdocs serve -w .

# FORMATTING AND CHECKING

# run the default complete prek suite
prek:
    uv run --group cicd prek run -a

# TESTING

pytest:
    @echo "run python tests"
    uv run --group cicd pytest

node-test:
    @echo "run dashboard js tests"
    node --test tests/unit/eval_dashboard/js/*.test.mjs

lychee:
    @echo "check links of the docs"
    uv run --group cicd properdocs build
    lychee --config lychee.toml --root-dir ./site "site/**/*.html"

# run all testing suites
test: pytest node-test lychee
    @echo "===All tests passed==="

# run tests and formatters
pr: prek test
    @echo "===The PR is clean==="
