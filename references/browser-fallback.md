# Browser tier: reading approved sources that headless tools can't

The last resort when `fetch_approved.py` prints `METHOD: none`, or when an approved
source is login-gated. A real Chrome session beats three things headless `curl`/WebFetch
cannot: the **TLS/JS-challenge** wall (Cloudflare/Akamai fingerprint the handshake, not
the user-agent), **rendered-only content** (SPA pages that build the DOM in JS), and
**authentication** (it carries logins you already have).

This is the same in-page `fetch()` technique used elsewhere in the toolkit: do the work
*inside the page's own origin* so requests carry its session cookies.

## When to use it

- `fetch_approved.py` exhausted its chain (`METHOD: none`).
- Cloudflare/Akamai JS-challenge that no headless request solves (e.g. Britannica, loc.gov HTML).
- Library lending books / journals you have a legitimate account for (e.g. Internet Archive
  search-inside, which 403s to curl but works in an authenticated session).

Stay inside the skill's contract: browser tier is for **approved domains** only, and only
for content you're authorized to read. A login-gated read of an approved source is still a
citation of that approved source -- it is not a license to defeat access controls on
anything else. Same restraint ethic as the rest of the methodology.

## The procedure (Claude-in-Chrome MCP)

Tools load via ToolSearch:
`select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__javascript_tool`

1. `tabs_context_mcp(createIfEmpty=true)` -- get a tab id (once per session).
2. `navigate(url, tabId)` -- load the approved page. This alone defeats the Cloudflare
   JS-challenge, because a real browser solves it.
3. **Extract with the DevTools console, not the mouse.** Prefer `javascript_tool`
   (in-page JS = the DevTools console) over visual clicking and screenshots: it is faster,
   exact, and survives layout changes. `get_page_text` grabs the main article but can pick
   the wrong block on pages with sidebars -- when it does, query the DOM directly.

### Reading a rendered article (e.g. a Cloudflare-walled encyclopedia)

```js
// Pull the real biography paragraphs, not a sidebar block.
const paras = [...document.querySelectorAll('p')].map(p => p.innerText.trim()).filter(Boolean);
paras.filter(t => /born|died|baptized|<your anchor terms>/i.test(t)).slice(0, 6);
```

### Reading a login-gated API from inside its origin (the "Shodan pattern")

Navigate to the site first so the code runs in its origin, then `fetch` with
`credentials:'include'` so your session cookies ride along. Worked example -- Internet
Archive full-text **search-inside** of a lending book (403s to curl, 200 here):

```js
const id='<archive-item-id>';
// metadata is same-origin; gives the current item server + path
const meta = await fetch(`https://archive.org/metadata/${id}`, {credentials:'include'}).then(r=>r.json());
const {server, dir} = meta;
const q = '"August 14, 1851"';   // quote a phrase for an exact-sequence search
const url = `https://${server}/fulltext/inside.php?item_id=${id}&doc=${id}&path=${dir}&q=${encodeURIComponent(q)}`;
const p = await fetch(url, {credentials:'include'}).then(r=>r.json());
p.matches.slice(0,5).map(m => ({page:m.par?.[0]?.page,
  text:(m.text||'').replace(/<\/?IA_FTS_MATCH>/g,'').replace(/\s+/g,' ').trim()}));
```

Notes:
- `inside.php` FTS tokenizes per word; quote a phrase (`'"August 14, 1851"'`) to find the
  exact sentence rather than scattered word hits.
- `m.par[0].page` is the scan page number -- usable provenance for the citation.
- Confirm session before trusting a 403/empty result: `/logged-in-user/.test(document.cookie)`.

## Citing browser-tier reads

The citation is still the original approved URL. Add a short provenance note so the read is
auditable:

```
[n] Category - "Title" - https://approved-url
    (read via authenticated browser session; <book/page or snapshot detail>)
```

## Avoid dialogs

Do not trigger `alert`/`confirm`/`prompt` or modal dialogs -- they block the MCP channel.
Read and extract; don't click destructive or irreversible controls.
