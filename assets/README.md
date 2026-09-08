# assets

This directory contains static binary assets that are committed to the repository and referenced directly in the README and PyPI project page. These are not source code files and are not part of the installable package distribution.

---

## Contents

| File | Description |
|---|---|
| `banner.png` | The official wide-format repository header banner. Generated at 1200x456 px. Used in `README.md` via an absolute `raw.githubusercontent.com` URL so that it renders correctly on both the GitHub repository page and the PyPI project description page. |
| `logo.png` | The original portrait-format version of the project mascot illustration used during the design iteration phase. Retained for archival purposes. |

---

## Usage in README

The banner is embedded at the top of `README.md` using an absolute raw GitHub URL:

```html
<p align="center">
  <img src="https://raw.githubusercontent.com/Edge-Explorer/Parse-Anything-/main/assets/banner.png"
       width="100%"
       style="max-width: 850px; border-radius: 8px;"
       alt="Parse-Anything Anime Manga Banner" />
</p>
```

Using the absolute `raw.githubusercontent.com` URL (rather than a relative path) is required because PyPI renders the README on the `pypi.org/project/universal-doc-parser` page and cannot resolve relative repository paths.

---

## Adding New Assets

When adding new assets to this directory:

1. Use descriptive, lowercase, underscore-separated filenames.
2. Prefer PNG for raster graphics. Use SVG for diagrams and icons when possible.
3. Compress images before committing. Images larger than 2 MB should be stored externally and referenced by URL.
4. Update this README with the new file entry and a clear description of its purpose and dimensions.
