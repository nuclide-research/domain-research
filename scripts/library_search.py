#!/usr/bin/env python3
"""
library_search.py - discover open, citeable library holdings for a query.

Encyclopedias are thin. For a real person, place, or event the better sources are
digitized books and library catalog records. This searches the open, keyless,
APPROVED-DOMAIN holdings APIs and returns citeable URLs (with a full-text flag),
so the research workflow can move from "an encyclopedia says" to "the scanned book
on archive.org, page-readable, says."

Sources queried (all on the approved allowlist, all keyless, none Cloudflare-walled):
  - Internet Archive  (archive.org)      - full-text scanned books; many readable in-browser
  - Open Library      (openlibrary.org)  - catalog + links to Internet Archive full text

This is a DISCOVERY/pointer tool. It tells you what exists and where. You still read
the actual item and verify the specific claim per the skill's Step 4 before citing.

Deliberately NOT included: shadow libraries (LibGen / Z-Library / Anna's Archive) and
"index of" open directories of copyrighted books. Two reasons, either one sufficient:
they are not on the approved allowlist (so they can never be a citation here), and
they distribute in-copyright works without authorization. The open surface below is
richer than it looks and keeps every result citeable.

Key-gated upgrades you can add later if you register for keys:
  - DPLA            (dp.la)             - aggregates U.S. library/museum/archive items
  - CORE            (core.ac.uk)        - open-access research papers
  - HathiTrust full-text                - public-domain book full text
For university institutional repositories and special collections, a domain-scoped
web search is the right pointer (e.g. allowed_domains=["edu","dp.la"]); those live
behind many different repository platforms with no single API.

Usage:
    python3 library_search.py "Doc Holliday biography" [--rows N]
"""
import sys
import json
import subprocess
import urllib.parse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get_json(url, timeout=30):
    try:
        out = subprocess.run(
            ["curl", "-s", "-L", "-A", UA, "--max-time", str(timeout), url],
            capture_output=True, timeout=timeout + 10).stdout
        return json.loads(out.decode("utf-8", "replace"))
    except Exception as e:
        return {"__error__": str(e)}


def search_internet_archive(query, rows):
    # title-scoped + texts-only keeps results to actual books/documents and
    # filters out podcasts, software, and group-dump noise that a broad
    # description match pulls in.
    q = "title:(%s) AND mediatype:texts" % query
    url = ("https://archive.org/advancedsearch.php?q=%s"
           "&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=year&fl[]=mediatype"
           "&sort[]=year+asc"
           "&rows=%d&output=json" % (urllib.parse.quote(q), rows))
    data = get_json(url)
    if "__error__" in data:
        return [], data["__error__"]
    out = []
    for d in data.get("response", {}).get("docs", []):
        ident = d.get("identifier")
        out.append({
            "year": d.get("year", "????"),
            "title": d.get("title", ""),
            "creator": d.get("creator", ""),
            "fulltext": True,  # archive.org items are readable/borrowable
            "url": "https://archive.org/details/%s" % ident if ident else "",
        })
    return out, None


def search_open_library(query, rows):
    url = ("https://openlibrary.org/search.json?q=%s&limit=%d"
           "&fields=title,author_name,first_publish_year,ia,key"
           % (urllib.parse.quote(query), rows))
    data = get_json(url)
    if "__error__" in data:
        return [], data["__error__"]
    out = []
    for w in data.get("docs", []):
        ia = (w.get("ia") or [None])[0]
        key = w.get("key", "")
        out.append({
            "year": w.get("first_publish_year", "????"),
            "title": w.get("title", ""),
            "creator": (w.get("author_name") or [""])[0],
            "fulltext": bool(ia),
            # prefer the readable Internet Archive copy when one exists
            "url": ("https://archive.org/details/%s" % ia) if ia
                   else ("https://openlibrary.org%s" % key),
        })
    return out, None


def main():
    if len(sys.argv) < 2:
        print('usage: library_search.py "<query>" [--rows N]', file=sys.stderr)
        return 2
    query = sys.argv[1]
    rows = 6
    if "--rows" in sys.argv:
        try:
            rows = int(sys.argv[sys.argv.index("--rows") + 1])
        except (ValueError, IndexError):
            pass

    for label, fn in (("Internet Archive (archive.org)", search_internet_archive),
                      ("Open Library (openlibrary.org)", search_open_library)):
        results, err = fn(query, rows)
        print("=" * 64)
        print(label)
        print("=" * 64)
        if err:
            print("  [error] %s" % err)
            continue
        if not results:
            print("  (no results)")
            continue
        for r in results:
            ft = "FULL-TEXT" if r["fulltext"] else "catalog  "
            creator = (" - " + r["creator"]) if r["creator"] else ""
            print("  [%s] %s  %s%s" % (ft, str(r["year"]).ljust(4),
                                       r["title"][:60], creator))
            print("            %s" % r["url"])
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
