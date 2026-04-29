#!/usr/bin/env bash
# test-site.sh — Build a Jekyll site and validate the output.
# Replaces the manual ten-step checklist that lived in the original
# jekyll-test SKILL.md.
#
# Usage:
#   test-site.sh              # tests the site at/above $PWD
#   test-site.sh /path/to/site
#
# Exits non-zero only if the Jekyll project cannot be found or the build
# itself fails. Validation findings (missing colors, missing permalinks,
# orphan navigation children, missing includes) are reported but do not
# fail the run — the agent reading the output decides what to do.

set -euo pipefail

START_DIR="${1:-$PWD}"

# --- Locate Jekyll root (walk up from START_DIR looking for _config.yml) ---
SITE_ROOT=""
dir="$(cd "$START_DIR" && pwd)"
while [[ "$dir" != "/" && "$dir" != "" ]]; do
  if [[ -f "$dir/_config.yml" ]]; then
    SITE_ROOT="$dir"
    break
  fi
  dir="$(dirname "$dir")"
done

if [[ -z "$SITE_ROOT" ]]; then
  echo "Error: no _config.yml found at or above $START_DIR — not a Jekyll project" >&2
  exit 1
fi

cd "$SITE_ROOT"
echo "Site root: $SITE_ROOT"

# --- Read selected _config.yml keys via Python (PyYAML if available, else regex) ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to parse _config.yml but was not found on PATH" >&2
  exit 1
fi

read_config() {
  python3 - <<'PY' 2>/dev/null
import os, sys, re
path = "_config.yml"
try:
    import yaml
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
except Exception:
    cfg = {}
    line_re = re.compile(r"^(\w+):\s*(.*)$")
    with open(path) as f:
        for line in f:
            m = line_re.match(line)
            if m:
                cfg[m.group(1)] = m.group(2).strip().strip('"').strip("'")
for key in ("color_scheme", "theme", "remote_theme", "baseurl", "url"):
    val = cfg.get(key, "")
    print(f"{key}={val}")
PY
}

declare -A CFG=()
while IFS='=' read -r k v; do
  [[ -n "$k" ]] && CFG["$k"]="$v"
done < <(read_config)

THEME="${CFG[theme]:-${CFG[remote_theme]:-}}"
COLOR_SCHEME="${CFG[color_scheme]:-}"

echo "Theme:        ${THEME:-<none>}"
echo "Color scheme: ${COLOR_SCHEME:-<none>}"

# --- Bundler dependencies ---
if ! command -v bundle >/dev/null 2>&1; then
  echo "Error: bundle (Bundler) is not on PATH — install Ruby + bundler first" >&2
  exit 1
fi

if ! bundle check >/dev/null 2>&1; then
  echo "Installing gem dependencies via 'bundle install'..."
  bundle install --quiet
fi

# --- just-the-docs search index init (only when used as a gem theme) ---
if [[ "$THEME" == "just-the-docs" && ! -f "assets/js/zzzz-search-data.json" ]]; then
  echo "Initialising just-the-docs search index..."
  bundle exec just-the-docs rake search:init >/dev/null 2>&1 || true
fi

# --- Build ---
echo
echo "Building site..."
BUILD_LOG="$(mktemp)"
trap 'rm -f "$BUILD_LOG"' EXIT
BUILD_OK=1
BUILD_TIME=""
if bundle exec jekyll build >"$BUILD_LOG" 2>&1; then
  BUILD_TIME="$(grep -oE 'done in [0-9.]+ seconds' "$BUILD_LOG" | tail -1 || echo)"
else
  BUILD_OK=0
fi

if [[ "$BUILD_OK" -eq 0 ]]; then
  echo "Build:        FAILED"
  echo "--- last 40 lines of build log ---"
  tail -40 "$BUILD_LOG"
  exit 1
fi
echo "Build:        OK ${BUILD_TIME:+($BUILD_TIME)}"

# --- Color scheme verification ---
COLOR_FOUND=0
COLOR_TOTAL=0
COLOR_MISSING=()
if [[ -n "$COLOR_SCHEME" ]]; then
  SCSS_FILE="_sass/color_schemes/${COLOR_SCHEME}.scss"
  if [[ -f "$SCSS_FILE" ]]; then
    # Pull every `#abcdef` hex from the SCSS file
    mapfile -t HEXES < <(grep -ohE '#[0-9a-fA-F]{3,8}' "$SCSS_FILE" | sort -u)
    COLOR_TOTAL=${#HEXES[@]}
    if [[ "$COLOR_TOTAL" -gt 0 ]]; then
      CSS_BLOB="$(cat _site/assets/css/*.css 2>/dev/null || true)"
      for hex in "${HEXES[@]}"; do
        if grep -qiF "$hex" <<<"$CSS_BLOB"; then
          ((COLOR_FOUND++)) || true
        else
          COLOR_MISSING+=("$hex")
        fi
      done
    fi
  fi
fi

# --- Permalink verification ---
PERMA_TOTAL=0
PERMA_OK=0
PERMA_MISSING=()
while IFS= read -r mdfile; do
  perma="$(awk '
    /^---$/ {fm = !fm; next}
    fm && /^permalink:/ {sub(/^permalink:[ \t]*/, ""); gsub(/["'\'']/, ""); print; exit}
  ' "$mdfile")"
  [[ -z "$perma" ]] && continue
  ((PERMA_TOTAL++)) || true
  perma_clean="${perma#/}"
  perma_clean="${perma_clean%/}"
  if [[ -f "_site/${perma_clean}/index.html" || -f "_site/${perma_clean}.html" ]]; then
    ((PERMA_OK++)) || true
  else
    PERMA_MISSING+=("$perma")
  fi
done < <(find . -type f -name '*.md' -not -path './_site/*' -not -path './vendor/*' -not -path './node_modules/*' 2>/dev/null)

# --- just-the-docs navigation consistency ---
NAV_PARENTS=0
NAV_CHILDREN=0
NAV_ORPHANS=()
if [[ "$THEME" == "just-the-docs" ]]; then
  declare -A PARENT_TITLES=()
  while IFS= read -r mdfile; do
    has_kids="$(awk '/^---$/{fm=!fm;next} fm && /^has_children:[ \t]*true/{print "yes";exit}' "$mdfile")"
    title="$(awk '/^---$/{fm=!fm;next} fm && /^title:/{sub(/^title:[ \t]*/,"");gsub(/["'\'']/,"");print;exit}' "$mdfile")"
    if [[ "$has_kids" == "yes" && -n "$title" ]]; then
      PARENT_TITLES["$title"]=1
      ((NAV_PARENTS++)) || true
    fi
  done < <(find . -type f -name '*.md' -not -path './_site/*' -not -path './vendor/*' 2>/dev/null)

  while IFS= read -r mdfile; do
    parent="$(awk '/^---$/{fm=!fm;next} fm && /^parent:/{sub(/^parent:[ \t]*/,"");gsub(/["'\'']/,"");print;exit}' "$mdfile")"
    [[ -z "$parent" ]] && continue
    ((NAV_CHILDREN++)) || true
    if [[ -z "${PARENT_TITLES[$parent]:-}" ]]; then
      NAV_ORPHANS+=("$mdfile -> parent:$parent")
    fi
  done < <(find . -type f -name '*.md' -not -path './_site/*' -not -path './vendor/*' 2>/dev/null)
fi

# --- Custom includes ---
INC_FOOTER="-"
INC_HEAD="-"
if [[ -f _includes/footer_custom.html ]]; then
  if grep -qF "$(head -3 _includes/footer_custom.html)" _site/index.html 2>/dev/null; then
    INC_FOOTER="ok"
  else
    INC_FOOTER="missing"
  fi
fi
if [[ -f _includes/head_custom.html ]]; then
  if grep -qF "$(head -3 _includes/head_custom.html)" _site/index.html 2>/dev/null; then
    INC_HEAD="ok"
  else
    INC_HEAD="missing"
  fi
fi

# --- Summary ---
echo
echo "Jekyll Site Test Results"
echo "========================"
echo "Theme:        ${THEME:-<none>}"
echo "Color scheme: ${COLOR_SCHEME:-<none>}"
echo "Build:        OK ${BUILD_TIME:+($BUILD_TIME)}"
if [[ -n "$COLOR_SCHEME" && "$COLOR_TOTAL" -gt 0 ]]; then
  echo "Colors:       $COLOR_FOUND/$COLOR_TOTAL custom colors found in CSS"
fi
echo "Pages:        $PERMA_OK/$PERMA_TOTAL permalinked pages built"
if [[ "$THEME" == "just-the-docs" ]]; then
  echo "Navigation:   $NAV_PARENTS parents, $NAV_CHILDREN children, ${#NAV_ORPHANS[@]} orphans"
fi
echo "Includes:     footer=$INC_FOOTER, head=$INC_HEAD"

# --- Failure detail (reported, not fatal) ---
if [[ ${#COLOR_MISSING[@]} -gt 0 ]]; then
  echo
  echo "Missing colors:"
  printf '  %s\n' "${COLOR_MISSING[@]}"
fi
if [[ ${#PERMA_MISSING[@]} -gt 0 ]]; then
  echo
  echo "Missing permalinked pages:"
  printf '  %s\n' "${PERMA_MISSING[@]}"
fi
if [[ ${#NAV_ORPHANS[@]} -gt 0 ]]; then
  echo
  echo "Orphan nav children (parent not found):"
  printf '  %s\n' "${NAV_ORPHANS[@]}"
fi
