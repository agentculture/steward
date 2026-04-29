# tests/shell/helpers.bash — shared bats helpers.
#
# Bats discovers files matching tests/shell/*.bats. Each file sources this
# file in setup() to get a consistent environment.

# Path to repo root (resolved at file-source time so tests can be invoked
# from anywhere — bats from the repo root, IDE from the test file dir, etc.).
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
export REPO_ROOT
export SKILLS_DIR="$REPO_ROOT/.claude/skills"

# Run a script under test, capturing stdout, stderr, and exit code into
# variables `output`, `stderr_output`, and `status`. Bats' built-in `run`
# merges stdout+stderr by default; use this when you need them separated.
run_script() {
    local stderr_file
    stderr_file=$(mktemp)
    output=$("$@" 2>"$stderr_file")
    status=$?
    stderr_output=$(cat "$stderr_file")
    rm -f "$stderr_file"
    return 0
}
