# Dev Data

- `public-sample.opml`: sanitized sample committed to the repository.
- `local-seed.opml`: optional personal OPML file (gitignored).
- `inoreader-default.opml`: legacy personal local file name (gitignored).

If `SIFT_DEV_SEED_OPML_PATH` points to a missing file, seed logic falls back to:

1. `dev-data/local-seed.opml`
2. `dev-data/public-sample.opml`
