#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/gh-issues/scripts/gh-issues.sh"

@test "gh-issues: no args exits 1 with usage" {
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "gh-issues: --repo with no value exits 1 (not unbound-variable)" {
    run bash "$SCRIPT" --repo
    [ "$status" -eq 1 ]
    [[ "$output" == *"--repo requires a value"* ]]
}

@test "gh-issues: --repo with empty string exits 1" {
    run bash "$SCRIPT" --repo "" 42
    [ "$status" -eq 1 ]
    [[ "$output" == *"--repo requires a value"* ]]
}
