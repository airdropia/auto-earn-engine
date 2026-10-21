# Pinterest distribution: the state and the method

## What is live

The Pinterest account `@x2newd` (business: **VectorForge Daily**, account id
`1133499937372822102`) has the site **claimed** and the full memorial pin set
published. Every pin links to the maker with the Pinterest referrer attached,
so the traffic is visible in the storefront analytics.

- Claimed domain: `https://airdropia.github.io/auto-earn-engine/`
- Board: `Cricut Ideas & Cut Files`
- Destination: `https://airdropia.github.io/auto-earn-engine/maker/?utm_source=Pinterest&utm_medium=organic`
- Machine readable list: `pins/published.json`

The pin images are the ones in `pins/`, which are already served publicly, so
nothing has to be uploaded anywhere else. Pinterest re-hosts them on
`i.pinimg.com` and keeps the original as the click-through target.

## The claim, step by step

1. Pinterest Business Hub, `Claim your website`.
2. Verification method **Add HTML tag**. The tag is
   `<meta name="p:domain_verify" content="..."/>` and it has to live in the
   `<head>` of the page that is served at the root of the claimed domain.
3. The domain field must end with a trailing slash, otherwise Pinterest
   answers `Files cannot be verified. Add a trailing slash (/) to your path.`
4. The tag has to be emitted by the builder, not by hand. The deployed site is
   a workflow artifact (`weekly-compilation.yml` runs `pipeline/build_site.py`
   and uploads the `site` directory to GitHub Pages), so a hand edit of
   `site/index.html` is overwritten by the next build. The tag therefore
   lives in `pipeline/build_site.py`, next to the Google verification tag.
5. The claim is visible in the Business Hub as the bare domain name instead of
   the "claim ..." prompt.

## The build that was blocking this

`weekly-compilation.yml` failed three times in a row at the quality gate with
`PNG preview missing for ...svg`. The flagship workflow had a
**Render high-res PNG for new designs (6500px)** step and the weekly workflow
did not, so the weekly products never got their previews and the gate
correctly refused to publish them. The same render step now runs in the
weekly workflow, and the build passes.

## Publishing a pin

The browser has to be the one that is already signed in, because Pinterest
guards the creator surface with a captcha that a fresh profile cannot pass.
With that session the flow is:

1. Open `https://www.pinterest.com/pin-creation-tool/`.
2. Upload the image with the file picker (the images are local, in `pins/`).
3. Fill the title, the description and the link.
4. Choose the board. The picker does not open on a pointer click, it opens
   with the keyboard: focus the board control, press Enter, type the board
   name, press Enter.
5. Press `Publish`.

Two traps worth remembering:

- `Save from URL` does not accept a direct image URL. Pinterest tries to
  scrape a page and shows its sad puzzle image instead. Use the file picker.
- Every new draft lands on the first board by default, which is
  `Seamless Patterns for Designers`, so the board always has to be set
  explicitly.
