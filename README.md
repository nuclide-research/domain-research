# domain-research

A Claude Code skill that answers research questions using **only** sources from a vetted
allowlist of authoritative domains. Every claim gets a direct, working URL. No unapproved
sources, no silent gap-filling, no general-knowledge filler dressed up as a citation.

## What it does

Point it at any factual question and it runs a fixed workflow: classify the question into
domain categories, search only approved domains, read the actual page (not a snippet),
verify the specific claim is present, and cite the exact URL. When approved sources do not
cover something, it says so plainly instead of reaching for an unvetted source.

The allowlist in `references/trustworthy-domains.md` holds roughly 490 domains across nine
categories (government, academic, scientific, legal, financial, standards bodies, reference,
news of record, and library/archive holdings). Subdomains inherit approval only when the
parent domain is explicitly listed, so there is no silent scope creep.

## Why it has scripts

Authoritative sources are often the hardest to fetch. Government and reference sites sit
behind edge bot-protection that returns 403 to any headless client. The skill treats that
as a transport problem, not a dead source, and walks a three-tier fallback:

1. **`scripts/fetch_approved.py`** - a real browser-header request, then the same host's
   machine-readable endpoint (e.g. a Library of Congress `.madsrdf.json`), then the Internet
   Archive snapshot of the approved page. The citation stays anchored to the original URL.
2. **`scripts/library_search.py`** - discovers open, citeable book holdings on Internet
   Archive and Open Library so a research answer can move from "an encyclopedia says" to
   "the scanned scholarly book, page-readable, says." Shadow libraries are deliberately
   excluded: they are not on the allowlist and they distribute in-copyright works without
   authorization.
3. **Browser tier** (`references/browser-fallback.md`) - the last resort for a source that
   is login-gated or behind a JS-challenge no headless request can solve. A real Chrome
   session carries the full browser fingerprint and any logins you already hold, so it reaches
   approved-domain content that no headless tool can. This stays inside the contract: approved
   domains only, authorized content only. It is not a tool for defeating access controls.

## Layout

```
domain-research/
  SKILL.md                          workflow and hard constraints
  references/
    trustworthy-domains.md          the ~490-domain allowlist
    browser-fallback.md             browser-tier procedure
  scripts/
    fetch_approved.py               403-resistant fetcher (direct -> data -> Wayback)
    library_search.py               open library/book discovery
```

## Install

Drop the `domain-research/` directory into `~/.claude/skills/`. The skill auto-registers and
triggers on research, fact-checking, and "cite this against a real source" requests.

## Usage example

Ask a normal research question. The skill picks up requests to fact-check, to find a
source, to cite a claim, or to research a topic against trusted domains.

```
> Tell me about Doc Holliday, every claim cited to an authoritative source.
```

It classifies the question (history/biography, spanning Reference, Academic, and
Government), then works the sources. The New Georgia Encyclopedia carries the rounded
biography. The National Park Service confirms the gunfight date and participants from a
second category, turning a single-encyclopedia claim into a two-domain agreement. The one
historically contested fact, his birth year, gets the deepest source: a digitized scholarly
monograph on the Internet Archive, read at the browser tier because the lending book returns
403 to every headless tool. The answer comes back structured:

```
Answer:
John Henry "Doc" Holliday (August 14, 1851 to November 8, 1887) was a Georgia-born
dentist who became one of the most recognized gamblers and gunmen of the American West...
He participated in the gunfight near the O.K. Corral on October 26, 1881 [1][2], and died
of tuberculosis in Glenwood Springs, Colorado, on November 8, 1887 [1].

On the birth-year confusion: some older references give 1852. That is the christening
date, not the birth. The family biography places the birth on August 14, 1851 (p. 47) and
the belated christening on March 21, 1852 (p. 51) [3], so the 1851 date is correct.

Sources Used:
[1] Reference - "John Henry 'Doc' Holliday (1851-1887)," New Georgia Encyclopedia -
    https://www.georgiaencyclopedia.org/articles/history-archaeology/john-henry-doc-holliday-1851-1887/
[2] Government - "Virgil Earp," Homestead National Historical Park, U.S. National Park
    Service - https://www.nps.gov/home/learn/historyculture/virgil-earp.htm
[3] Reference - Karen Holliday Tanner, Doc Holliday: A Family Portrait (Univ. of Oklahoma
    Press, 1998), pp. 47, 51 - https://archive.org/details/dochollidayfamil0000tann
    (read via authenticated browser session; the lending book 403s to headless tools)

Issues Encountered:
- Birth-year discrepancy (1851 vs 1852) reported and resolved rather than silently picked.
```

The shape is the point: a synthesized answer, every claim keyed to a direct URL, conflicts
surfaced instead of hidden, and the access path noted as provenance when a source needed the
browser tier to reach.

## The contract

1. No claim from a domain absent from the allowlist, however credible it looks.
2. No vague citations. Every citation is a specific, direct, clickable URL.
3. No silent gap-filling. If approved sources do not answer the question, it says so.
4. No mixing unapproved snippets into an otherwise-approved answer.
