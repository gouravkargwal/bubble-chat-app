# Cookd GitHub Pages (Temporary)

This folder is ready to publish with GitHub Pages for Play Console policy links.

## Files

- `index.html` — landing page
- `privacy-policy.html` — public privacy policy URL
- `delete-account.html` — public account/data deletion URL

## Enable GitHub Pages

1. Push this repo/branch to GitHub.
2. Open repository `Settings` -> `Pages`.
3. Under **Build and deployment**, set:
   - **Source**: `Deploy from a branch`
   - **Branch**: your default branch (for example `main`)
   - **Folder**: `/docs`
4. Save and wait for the site to publish.

Your URLs will look like:

- `https://<github-username>.github.io/<repo>/privacy-policy.html`
- `https://<github-username>.github.io/<repo>/delete-account.html`

Use these in Google Play Console:

- Data safety -> **Delete account URL**
- Data safety -> **Delete data URL** (optional, can reuse delete-account URL)
- Store listing -> **Privacy policy URL** (privacy-policy URL)
