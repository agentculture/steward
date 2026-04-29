---
name: jekyll-test
description: >
  Build a Jekyll site (GitHub Pages / Cloudflare Pages) and validate the
  output: build succeeds, custom color scheme is applied, permalinked pages
  exist, just-the-docs navigation is consistent. Use after editing
  `_config.yml`, theme files, SCSS, or page front matter; or when the user
  says "test the site", "did the site build", "check jekyll", or
  "verify pages".
---

# Jekyll Test

Conditional skill — only meaningful when the sibling repo ships a Jekyll
site. Detected by the presence of `_config.yml` somewhere in the repo.

The original version of this skill was a ten-step manual checklist. The
script does all ten steps in one shot and prints a single-screen summary;
follow the script, not a manual procedure.

## Usage

```bash
# Test the site whose _config.yml is at or above the current directory
bash .claude/skills/jekyll-test/scripts/test-site.sh

# Test a specific site (path to repo root)
bash .claude/skills/jekyll-test/scripts/test-site.sh /path/to/jekyll-site
```

## What the script checks

1. **Locate root** — finds the nearest `_config.yml` (cwd, then walking up).
   Exits with a clear error if no Jekyll project is detected.
2. **Build** — runs `bundle install --quiet` then `bundle exec jekyll build`.
   A non-zero build is the only hard-fail; all later checks are reported
   but do not change the exit code.
3. **Custom colors** — if `_config.yml` declares `color_scheme: <name>` and
   `_sass/color_schemes/<name>.scss` exists, extracts hex values from that
   SCSS file and verifies each appears in the built `_site/assets/css/*`.
4. **Permalinks** — finds every page with `permalink:` front matter and
   confirms the corresponding `<permalink>/index.html` was generated.
5. **just-the-docs nav** — for sites using `just-the-docs`, validates that
   every `parent:` value in front matter matches a real parent page's
   `title:`, and flags parents that have no children.
6. **Includes** — checks that `_includes/footer_custom.html` and
   `_includes/head_custom.html` (if they exist) are spliced into
   `_site/index.html`.

The output is a single summary block matching the original SKILL.md prose.

## Requirements

- `bundle` (Bundler) on PATH.
- `ruby` on PATH (whatever the site's `Gemfile` requires).
- A Jekyll project (must contain `_config.yml`).
