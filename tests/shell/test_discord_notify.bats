#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/discord-notify/scripts/send-discord.sh"

@test "discord-notify: missing message exits 1" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"No message provided"* ]]
}

@test "discord-notify: missing DISCORD_WEBHOOK_URL exits 1" {
    unset DISCORD_WEBHOOK_URL || true
    run env -u DISCORD_WEBHOOK_URL bash "$SCRIPT" "hello"
    [ "$status" -eq 1 ]
    [[ "$output" == *"DISCORD_WEBHOOK_URL"* ]]
}

@test "discord-notify: --type with no value exits 1 (not unbound-variable)" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT" --type
    [ "$status" -eq 1 ]
    [[ "$output" == *"--type requires a value"* ]]
}

@test "discord-notify: --title with no value exits 1" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT" --title
    [ "$status" -eq 1 ]
    [[ "$output" == *"--title requires a value"* ]]
}

@test "discord-notify: --username with no value exits 1" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT" --username
    [ "$status" -eq 1 ]
    [[ "$output" == *"--username requires a value"* ]]
}

@test "discord-notify: unknown option exits 1" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT" --bogus
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

@test "discord-notify: bad --type value exits 1" {
    DISCORD_WEBHOOK_URL="x" run bash "$SCRIPT" --type nonsense "msg"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown type"* ]]
}
