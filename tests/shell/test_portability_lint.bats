#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/pr-review/scripts/portability-lint.sh"

setup() {
    TMPDIR_TEST=$(mktemp -d)
    cd "$TMPDIR_TEST"
    git init -q
    git config user.email "test@example.com"
    git config user.name "Test"
    git commit -q --allow-empty -m "init"
}

teardown() {
    cd /tmp
    rm -rf "$TMPDIR_TEST"
}

@test "portability-lint: --all on empty repo prints 'no tracked files' and exits 0" {
    run bash "$SCRIPT" --all
    [ "$status" -eq 0 ]
    [[ "$output" == *"no tracked files"* ]]
}

@test "portability-lint: --all on clean tracked file passes" {
    echo "Clean content with no leaks." > README.md
    git add README.md
    git commit -q -m "add README"
    run bash "$SCRIPT" --all
    [ "$status" -eq 0 ]
    [[ "$output" == *"clean"* ]]
}

@test "portability-lint: --all flags absolute home paths" {
    # Build the fixture at runtime so the bats source itself doesn't
    # carry a contiguous /home/<user>/ substring (which would trip the
    # lint when it scans this test file via doctor / pre-commit).
    local home_prefix="/home"
    printf 'See `%s/alice/secret/path`.\n' "$home_prefix" > docs.md
    git add docs.md
    git commit -q -m "add docs"
    run bash "$SCRIPT" --all
    [ "$status" -eq 1 ]
    [[ "$output" == *"Hard-coded /home"* ]]
}

@test "portability-lint: --all flags ~/.dotfile refs in committed docs" {
    # Same trick: keep the literal `~/.<dotfile>` string out of the
    # bats source. Construct it via concatenation at runtime.
    local tilde="~"
    printf 'Edit `%s/.bashrc` to set the variable.\n' "$tilde" > docs.md
    git add docs.md
    git commit -q -m "add docs"
    run bash "$SCRIPT" --all
    [ "$status" -eq 1 ]
    [[ "$output" == *"Per-user"* ]]
}

@test "portability-lint: ~/.claude/skills/.../scripts/ carve-out is allowed" {
    local tilde="~"
    printf 'Run `bash %s/.claude/skills/foo/scripts/bar.sh`.\n' "$tilde" > docs.md
    git add docs.md
    git commit -q -m "add docs"
    run bash "$SCRIPT" --all
    [ "$status" -eq 0 ]
    [[ "$output" == *"clean"* ]]
}

@test "portability-lint: default mode fails when working tree has untracked files but no diff" {
    # Repo with HEAD (init commit) and an untracked file. Default mode looks
    # at the diff vs HEAD, which is empty, but untracked files exist. The
    # tightened script should refuse to silently exit 0.
    echo "anything" > untracked.md
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"untracked files"* ]]
}

@test "portability-lint: default mode genuinely empty repo prints 'no files' and exits 0" {
    # No untracked files, no diff against HEAD.
    run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"no files to check"* ]]
}

@test "portability-lint: bad mode arg exits 2" {
    run bash "$SCRIPT" --bogus
    [ "$status" -eq 2 ]
    [[ "$output" == *"Usage:"* ]]
}
