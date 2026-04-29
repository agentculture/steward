#!/usr/bin/env bats

load helpers

SCRIPT="$SKILLS_DIR/run-tests/scripts/test.sh"

@test "run-tests: prints the command it will run before exec'ing" {
    # Stub `uv` so the script doesn't actually launch pytest. We point uv at
    # /bin/true via a temp dir on PATH and rely on the script to print the
    # command before exec.
    TMPBIN=$(mktemp -d)
    cat >"$TMPBIN/uv" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "$TMPBIN/uv"
    PATH="$TMPBIN:$PATH" run bash "$SCRIPT" -p -q
    rm -rf "$TMPBIN"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Running: uv run pytest"* ]]
    [[ "$output" == *"-n auto"* ]]
    [[ "$output" == *"-q"* ]]
}

@test "run-tests: --ci adds --cov + xml report + verbose" {
    TMPBIN=$(mktemp -d)
    cat >"$TMPBIN/uv" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "$TMPBIN/uv"
    PATH="$TMPBIN:$PATH" run bash "$SCRIPT" --ci
    rm -rf "$TMPBIN"
    [ "$status" -eq 0 ]
    [[ "$output" == *"--cov"* ]]
    [[ "$output" == *"coverage.xml"* ]]
    [[ "$output" == *"-v"* ]]
}

@test "run-tests: extra positional args are passed through to pytest" {
    TMPBIN=$(mktemp -d)
    cat >"$TMPBIN/uv" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
    chmod +x "$TMPBIN/uv"
    PATH="$TMPBIN:$PATH" run bash "$SCRIPT" -p tests/test_cli.py -k specific
    rm -rf "$TMPBIN"
    [ "$status" -eq 0 ]
    [[ "$output" == *"tests/test_cli.py"* ]]
    [[ "$output" == *"-k"* ]]
    [[ "$output" == *"specific"* ]]
}
