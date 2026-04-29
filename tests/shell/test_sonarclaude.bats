#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/sonarclaude/scripts/sonar.sh"

@test "sonarclaude: --help exits 0 and prints usage" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage: sonar.sh"* ]]
    [[ "$output" == *"Commands:"* ]]
}

@test "sonarclaude: -h is a synonym for --help" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "sonarclaude: missing SONAR_TOKEN exits 1" {
    run env -u SONAR_TOKEN bash "$SCRIPT" status --project p
    [ "$status" -eq 1 ]
    [[ "$output" == *"SONAR_TOKEN"* ]]
}

@test "sonarclaude: no command exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No command provided"* ]]
}

@test "sonarclaude: --project with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" --project
    [ "$status" -eq 1 ]
    [[ "$output" == *"--project requires a value"* ]]
}

@test "sonarclaude: --severity with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" --severity
    [ "$status" -eq 1 ]
    [[ "$output" == *"--severity requires a value"* ]]
}

@test "sonarclaude: --type with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" --type
    [ "$status" -eq 1 ]
    [[ "$output" == *"--type requires a value"* ]]
}

@test "sonarclaude: --limit with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" --limit
    [ "$status" -eq 1 ]
    [[ "$output" == *"--limit requires a value"* ]]
}

@test "sonarclaude: --issue with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" accept --issue
    [ "$status" -eq 1 ]
    [[ "$output" == *"--issue requires a value"* ]]
}

@test "sonarclaude: --comment with no value exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" accept --comment
    [ "$status" -eq 1 ]
    [[ "$output" == *"--comment requires a value"* ]]
}

@test "sonarclaude: missing project key exits 1" {
    run env -u SONAR_PROJECT bash -c "SONAR_TOKEN=x bash '$SCRIPT' status"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No project key"* ]]
}

@test "sonarclaude: accept without --issue exits 1" {
    SONAR_TOKEN=x SONAR_PROJECT=p run bash "$SCRIPT" accept
    [ "$status" -eq 1 ]
    [[ "$output" == *"requires --issue"* ]]
}

@test "sonarclaude: accept with --issue but no --comment exits 1" {
    SONAR_TOKEN=x SONAR_PROJECT=p run bash "$SCRIPT" accept --issue ABC
    [ "$status" -eq 1 ]
    [[ "$output" == *"requires --comment"* ]]
}

@test "sonarclaude: unknown option exits 1" {
    SONAR_TOKEN=x run bash "$SCRIPT" --bogus
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}
