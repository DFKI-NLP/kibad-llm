# `just` is a command runner.
# Install it by running: `uv tool install rust-just`.
# List available commands by running: `just -l`
# Get help from: `just --help`

# run the pr recipe. (The first recipe is the default one if `just` is run without a specific recipe: `$ just`)
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

# run python tests
pytest:
    uv run --group cicd pytest

# run dashboard js tests
node-test:
    node --test tests/unit/eval_dashboard/js/*.test.mjs

# check links of the docs
lychee:
    uv run --group cicd properdocs build
    lychee --config lychee.toml --root-dir ./site "site/**/*.html"

# run all testing suites
test: pytest node-test lychee
    @echo "===All tests passed==="

# run tests and formatters
pr: prek test
    @echo "===The PR is clean==="
