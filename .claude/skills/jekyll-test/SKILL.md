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

The script walks up to find `_config.yml`, runs `bundle install --quiet`
and `bundle exec jekyll build` (the only hard-fail step), then reports
non-fatal validation findings:

- Build status and elapsed time.
- For `color_scheme: <name>` declarations, every hex from
  `_sass/color_schemes/<name>.scss` is grep'd for in the built
  `_site/assets/css/*` — missing colors are listed.
- Every `permalink:` in front matter is checked against the generated
  `<permalink>/index.html` — missing pages are listed.
- For `just-the-docs` sites, every `parent:` value is matched against
  parent pages' `title:` — orphans (children whose parent is not found)
  are listed. Parent counts and child counts are printed.
- `_includes/footer_custom.html` and `_includes/head_custom.html`, if
  they exist, are checked for inclusion in `_site/index.html`.

The output is a single summary block plus per-category failure detail.

## Requirements

- `bundle` (Bundler) on PATH.
- `ruby` on PATH (whatever the site's `Gemfile` requires).
- `python3` on PATH (used to parse `_config.yml`; PyYAML preferred,
  regex fallback if it is not installed).
- A Jekyll project (must contain `_config.yml`).
