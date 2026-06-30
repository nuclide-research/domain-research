---
name: domain-research
description: Answers research questions using ONLY sources from a vetted allowlist of authoritative domains (government, academic, scientific, legal, financial, standards bodies). Every claim gets a direct URL. No unapproved sources, no silent gap-filling. Use this skill whenever the user wants fact-checked answers with citations, wants to verify a claim against authoritative sources, asks for sourced research on any topic, or explicitly wants results only from trusted/official domains. Also invoke when the user says things like "find me a source for", "what does [official body] say about", "cite this", or "back this up with real sources".
---

# Domain-Restricted Research

You answer questions using **only** sources from the approved domain list at `references/trustworthy-domains.md`. Read that file now -- you need the categories and domains before doing anything else.

## The process

### 1. Classify the question
Map the question to one or more domain categories (Academic, Government, Scientific, Legal, Financial, etc.). This determines where to search first and avoids wasted effort. A question can span categories -- a drug approval question touches Scientific, Government (FDA), and Legal.

### 2. Probe WebFetch availability, then search
Before searching, confirm WebFetch works by fetching a small, reliably-open approved URL (e.g., `https://www.cdc.gov/` or `https://github.com/`). One host failing does not mean WebFetch is down -- that host may simply be challenge-walled, which Step 4 handles. Only if **two** different approved hosts both fail to return content is WebFetch actually unavailable here. In that case, immediately surface it to the user: state that page content cannot be directly verified, that you will fall back to search snippets, and that all claims in the answer will be explicitly labeled **[snippet-sourced, not page-verified]**. Then continue with the rest of the workflow under that constraint -- do not abort.

Scope searches to relevant domains -- e.g., `site:nih.gov [topic]`. Use a general search engine as a **pointer layer only** (to find whether an approved domain has a relevant page). The search result snippet is never the citation -- only fetched page content is, or if WebFetch is unavailable, the snippet with explicit flagging per the fallback label above.

**Going deeper than encyclopedias.** For a real person, place, event, or anything with a literature behind it, an encyclopedia entry is the thin end. Two moves reach the substantial sources, both yielding citeable approved-domain URLs:

- **Digitized books** -- run `python3 scripts/library_search.py "<topic>"`. It queries Internet Archive and Open Library (both approved, keyless) and returns scanned full-text books with readable URLs. A page in the scholarly biography beats a paragraph in the encyclopedia.
- **University & archive holdings** -- the allowlist's blanket `.edu` rule already covers every university institutional repository, special collection, and digital library. Point a domain-scoped search at them: `allowed_domains=["edu","dp.la"]`. This surfaces primary sources (portraits, court records, historical markers, finding aids) held by the institutions closest to the subject -- often far richer than any encyclopedia. Validate and read each hit per Steps 3-4 as usual.

### 3. Validate every source before use
Before using any source, confirm its root domain is on the approved list. Subdomains inherit approval only if the parent domain is explicitly listed (`cancer.gov` is approved because `cancer.gov` is listed; `randomblog.cancer-info.com` is not approved because it is not).

### 4. Extract and verify the claim
Read the actual page content -- not just a snippet. Confirm the specific fact is genuinely present before using it. Do not infer or extrapolate beyond what the source states.

**When WebFetch does not return usable page content from an approved domain**, treat it as a transport problem, not a dead source -- the page is still approved, you just need a different door. This is the most common failure in practice and it is *not* limited to an explicit 403. An audit of this allowlist found dozens of perfectly readable approved hosts that WebFetch reported as a non-403 failure: a timeout, a connection refused, an empty or near-empty body, a redirect that lands on a login page or an unrelated host instead of the content, or any non-2xx status (402, 404, 405, 418, 429, 5xx). Keying recovery on the status code alone silently drops every one of those readable sources. Key it on the outcome instead: *did I get the actual page content?* If the answer is no, for any reason, recover -- do not report the source dead yet.

**Step 4a -- retry once.** Many failures are one-shot flakes: a transient timeout, a network drop, a redirect that resolves on the second hop. Re-run the exact same WebFetch a single time. If the retry returns the content, you are done; no heavier tier is needed.

**Step 4b -- managed-challenge shortcut.** If the failed response body carries a JS-challenge marker ("Just a moment", "Attention Required", "Checking your browser", `cf-chl`, `chlray`), a header-only request cannot solve it. Skip the direct door entirely and go straight to the browser tier (Step 4d). Spending a `fetch_approved.py` round trip on a managed challenge only wastes a call.

**Step 4c -- run the bundled fetcher** for everything else (a plain 403/4xx/5xx, a timeout, a redirect-to-nowhere, an empty body):

```
python3 scripts/fetch_approved.py "<the-failed-url>" --max-chars 8000
```

It tries, in order: (1) a real browser-header request that also follows redirects, (2) the same host's machine-readable endpoint (e.g. LOC `.madsrdf.json`), (3) the Internet Archive snapshot of the page (`archive.org` is itself on the approved list, so a snapshot is a faithful read of the approved page -- keep citing the original URL and note the snapshot date as provenance). The output's first lines tell you which door worked (`METHOD: direct|data|wayback`).

**Step 4d -- browser tier.** If the script prints `METHOD: none`, or the content is login-gated (a Cloudflare JS-challenge that headless requests can't solve, a library lending book, a journal you have legitimate access to), escalate to the **browser tier** before giving up -- see `references/browser-fallback.md`. A real Chrome session carries the full browser TLS fingerprint, solves the JS challenge, and (the decisive part) holds your existing logins, so it reaches approved-domain content that no headless tool can. This is the same in-page `fetch()` technique used elsewhere in the toolkit: navigate to the approved page, then run JavaScript in the page context (`credentials:'include'`) so the request carries your session. A login-gated read of an approved source is still a citation of that approved source -- note "read via authenticated browser session" as provenance. Only report a source inaccessible after the browser tier also fails.

### 5. Cite with a direct, working URL
Every factual claim gets the direct URL to the specific page, not the homepage. Multiple claims from the same page can share one citation.

### 6. Cross-check when possible
If more than one approved domain covers the same fact, check both. If they conflict, report the conflict -- don't silently pick one.

### 7. Compile the answer
Write the synthesized answer with inline citation markers `[1]`, `[2]`, etc. Follow with a source log.

### 8. Report issues transparently
If approved sources don't cover the question, say so explicitly. Never fall back to unapproved sources or fill gaps from general knowledge without flagging it.

## Issue handling

| Situation | Response |
|---|---|
| No approved domain covers the topic | State plainly that no source on the approved list addresses this |
| Approved domain exists but specific page not found | State what was searched and which domains were checked |
| WebFetch unavailable in this environment | State this upfront in Step 2; use search snippets as fallback; label every snippet-sourced claim **[snippet-sourced, not page-verified]** inline |
| WebFetch fails to return page content (403, timeout, empty body, redirect-to-login, 402/404/405/418/429/5xx) | Not a dead source, and not only the 403 case -- this is the common failure. Retry once (Step 4a); if a JS-challenge marker is present go straight to the browser tier (Step 4b); otherwise run `scripts/fetch_approved.py <url>` (browser-headers -> data endpoint -> Wayback snapshot). If `METHOD: none`, escalate to the browser tier (`references/browser-fallback.md`) before reporting inaccessible |
| Content is login-gated (lending book, paywall you have access to, hard JS-challenge) | Use the browser tier: a real Chrome session carries your logins and solves JS-challenges. In-page `fetch(..., {credentials:'include'})` reaches gated APIs (e.g. Internet Archive search-inside). See `references/browser-fallback.md`. Cite as "read via authenticated browser session" |
| Source found but paywalled/inaccessible | Note the domain and page title; do not assert claims from it |
| Sources conflict | Present both claims with links; flag the discrepancy |
| Relevant result on unapproved domain | Note it exists but was excluded per domain policy; do not cite or link it |
| Approved domain genuinely dead, after the full chain | Only once retry (Step 4a) + `fetch_approved.py` (Step 4c) + browser tier (Step 4d) have all failed, or DNS does not resolve at all: report the failed URL and continue checking other approved domains. A first-try error is never enough to call a source dead |

## Output format

```
Answer:
<synthesized answer with inline citation markers [1] [2] ...>

Sources Used:
[1] Category - "Page Title" - https://exact-url
[2] Category - "Page Title" - https://exact-url

Issues Encountered:
- <any domain that returned nothing, conflicted, was inaccessible, or fell outside the approved list>
(omit this section if no issues occurred)
```

## Hard constraints

1. No claim from a domain absent from the approved list -- regardless of how credible it appears.
2. No vague citations ("a government source says...") -- every citation is a specific, direct, clickable URL.
3. No silent gap-filling -- if approved sources don't answer the question, state that.
4. No mixing unapproved snippets into an answer even if other citations in the same answer are approved.
