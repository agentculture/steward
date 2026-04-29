#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/jekyll-test/scripts/test-site.sh"

setup() {
    TMPDIR_TEST=$(mktemp -d)
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

@test "jekyll-test: no _config.yml in or above target exits 1" {
    run bash "$SCRIPT" "$TMPDIR_TEST"
    [ "$status" -eq 1 ]
    [[ "$output" == *"no _config.yml"* ]]
    [[ "$output" == *"not a Jekyll project"* ]]
}

@test "jekyll-test: defaults to PWD when no arg given" {
    cd "$TMPDIR_TEST"
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"no _config.yml"* ]]
}
