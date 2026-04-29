#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/notebooklm/scripts/get-repo-sources.sh"

@test "notebooklm: --help exits 0 and prints usage" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: get-repo-sources.sh"* ]]
}

@test "notebooklm: -h is a synonym for --help" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "notebooklm: --branch with no value exits 1 (not unbound-variable)" {
    run bash "$SCRIPT" --branch
    [ "$status" -eq 1 ]
    [[ "$output" == *"--branch requires a value"* ]]
}

@test "notebooklm: unknown option exits 1" {
    run bash "$SCRIPT" --bogus
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

@test "notebooklm: outside a git repo exits 1" {
    TMPDIR_TEST=$(mktemp -d)
    cd "$TMPDIR_TEST"
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not inside a git repository"* ]]
    rm -rf "$TMPDIR_TEST"
}
