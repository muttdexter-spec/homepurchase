# deliverables

`pipeline/refresh.sh` writes the regenerated report here:

- `Walking-the-Shortlist.html` — standalone build
- `walking-the-shortlist.artifact-src.html` — body-only build
- `renovation-cost-detail.md`

To publish a new version, copy the desktop build over `full.html` and the phone build
over `mobile.html` at the repository root, then commit.

These outputs are not kept in the repository, only the published copies at the root are.
