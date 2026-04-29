#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/pypi-maintainer/scripts/switch-source.sh"

@test "pypi-maintainer: no args exits 1 with usage" {
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "pypi-maintainer: --help exits 0 and prints usage" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "pypi-maintainer: -h is a synonym for --help" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "pypi-maintainer: --version with no value exits 1 (not unbound-variable)" {
    run bash "$SCRIPT" --version
    [ "$status" -eq 1 ]
    [[ "$output" == *"--version requires a value"* ]]
}

@test "pypi-maintainer: --path with no value exits 1" {
    run bash "$SCRIPT" --path
    [ "$status" -eq 1 ]
    [[ "$output" == *"--path requires a value"* ]]
}

@test "pypi-maintainer: only one positional arg exits 1 with usage" {
    run bash "$SCRIPT" some-package
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "pypi-maintainer: unknown source exits 1" {
    run bash "$SCRIPT" some-package nonsense-source
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown source: nonsense-source"* ]]
}

@test "pypi-maintainer: unknown option exits 1" {
    run bash "$SCRIPT" --bogus
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

@test "pypi-maintainer: local mode with no pyproject.toml exits 1" {
    TMPDIR_TEST=$(mktemp -d)
    run bash "$SCRIPT" some-package local --path "$TMPDIR_TEST"
    [ "$status" -eq 1 ]
    [[ "$output" == *"does not contain a pyproject.toml"* ]]
    rm -rf "$TMPDIR_TEST"
}
