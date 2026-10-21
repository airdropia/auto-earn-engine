# Pinterest API: what works, what does not

The Pinterest developer app exists: `VectorForge Daily`, app id `1604703`,
trial access active, redirect URI
`https://airdropia.github.io/auto-earn-engine/oauth-callback`. The secret and
the tokens live in `~/.pi/secrets/pinterest.env`, never in git.

## What works today

### Read scope, straight from the dashboard

`https://developers.pinterest.com/apps/1604703/` has a **Generate Access
Tokens** panel. Pressing **Generate token** returns a `pina_...` token that is
valid for 24 hours and carries `pins:read`, `boards:read`, `user_accounts:read`,
`ads:read` and `catalogs:read`. The token is displayed once, behind a
`show or hide` eye button; the real value is in the text node, so it can be
read straight out of the DOM and written to the secrets file.

That token is enough for the measurement loop:

```
GET https://api.pinterest.com/v5/boards
GET https://api.pinterest.com/v5/pins?page_size=20
GET https://api.pinterest.com/v5/pins/{pin_id}/analytics?metric_types=IMPRESSION,PIN_CLICK,SAVE,OUTBOUND_CLICK&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
```

The analytics call needs `start_date`; without it the API answers
`Parameter 'start_date' is required`. This is the only honest way to answer
"will they actually click", so it is the metric that decides which product
families get more pins.

### Writes, through the browser

Writing needs `pins:write` and `boards:write`. The OAuth exchange for those
scopes is currently blocked: the authorize step works (the dashboard shows
`Give access` and the callback carries a code), but the token exchange
answers `401 Authentication failed` with a fresh code, the dashboard secret,
and a fresh app secret after a reset. The accepted body format is JSON, the
form encoded body is rejected with `Invalid request body`, and a code can only
be used once, so a failed attempt poisons the next one. That is why the pins
were published through the creator UI instead.

## The publish flow that works

1. `https://www.pinterest.com/pin-creation-tool/`
2. Upload the image with the file picker. `Save from URL` does not accept a
   direct image URL: Pinterest tries to scrape a page and answers with its sad
   puzzle image.
3. Fill the title, the description and the link.
4. Choose the board. The picker only opens with the keyboard: focus the board
   control, press Enter, type the board name, press Enter. A pointer click
   does nothing, and the new draft defaults to the first board, so the board
   always has to be set.
5. Press `Publish`.

## Moving pins between boards

The API cannot do it without the write scope, but the UI can move pins in
bulk:

1. Open the board, then **More Board options** -> **Organize**.
2. **Select all** -> **Move Pins** -> pick the target board -> confirm.

This is how the nine memorial pins were moved off `Seamless Patterns for
Designers` and onto `Cricut Ideas & Cut Files`, which is the board that
matches the product.
