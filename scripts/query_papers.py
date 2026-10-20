#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArXiv & ArXivDaily Paper Retrieval Tool
Fetches, filters, ranks, and enriches academic papers based on user-defined domains and dates.
"""

import os
import re
import sys
import json
import time
import argparse
import urllib3
import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

urllib3.disable_warnings()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_FILE = os.path.join(SCRIPT_DIR, "domain_presets.json")
LOCAL_CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.local.json")


def load_credentials():
    username = os.environ.get("ARXIVDAILY_USERNAME", "")
    password = os.environ.get("ARXIVDAILY_PASSWORD", "")
    if os.path.exists(LOCAL_CONFIG_FILE):
        try:
            with open(LOCAL_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                username = username or cfg.get("username", "")
                password = password or cfg.get("password", "")
        except Exception:
            pass
    return username, password


def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load domain presets: {e}", file=sys.stderr)
    return {}


class ArxivDailyClient:
    def __init__(self, username=None, password=None):
        default_user, default_pass = load_credentials()
        self.username = username or default_user
        self.password = password or default_pass
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Connection": "close"
        })
        self.username = username
        self.password = password
        self.logged_in = False

    def login(self):
        login_url = "https://www.arxivdaily.com/login"
        for attempt in range(3):
            try:
                r = self.session.get(login_url, timeout=15)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                csrf_inp = soup.find("input", {"name": "csrf_token"})
                csrf = csrf_inp["value"] if csrf_inp else ""
                login_data = {
                    "username": self.username,
                    "password": self.password,
                    "csrf_token": csrf
                }
                r_post = self.session.post(login_url, data=login_data, timeout=15)
                if r_post.status_code in (200, 302):
                    self.logged_in = True
                    print(f"[*] Successfully logged into arXivDaily as {self.username}")
                    return True
            except Exception as e:
                print(f"[!] Login attempt {attempt + 1} failed: {e}", file=sys.stderr)
                time.sleep(1.5)
        print("[!] Warning: Could not log into arXivDaily. Advanced features might be limited.", file=sys.stderr)
        return False

    def parse_paper_cards(self, soup):
        results = []
        cards = soup.find_all("article", class_="paper-card") or soup.find_all("div", class_="paper-card")
        if not cards:
            cards = soup.select(".card")
        
        for card in cards:
            aid = card.get("id", "").replace("paper-", "").replace("-", ".")
            title_en_el = card.find("h2") or card.find("h3") or card.select_one(".paper-title")
            title_en = title_en_el.get_text(strip=True) if title_en_el else ""
            
            # If aid wasn't in card id, try to find from link
            if not aid:
                link_el = card.find("a", href=re.compile(r"arxiv\.org/abs/")) or card.find("a", href=re.compile(r"/abs/"))
                if link_el and link_el.get("href"):
                    m = re.search(r"(\d{4}\.\d{4,5})", link_el["href"])
                    if m:
                        aid = m.group(1)
            
            if not aid:
                continue

            title_cn_el = card.find("p", class_="title-cn")
            title_cn = title_cn_el.get_text(strip=True) if title_cn_el else ""

            summary_el = card.find("p", class_="summary") or card.find("div", class_="paper-abstract")
            summary = summary_el.get_text(strip=True) if summary_el else ""
            if summary.startswith("AI总结"):
                summary = re.sub(r"^AI总结[:：\s]*", "", summary).strip()

            cats = [c.get_text(strip=True) for c in card.find_all("span", class_="category-pill") or card.select(".badge")]
            authors_el = card.find("p", class_="authors")
            authors = authors_el.get_text(strip=True) if authors_el else ""

            results.append({
                "arxiv_id": aid,
                "title_en": title_en,
                "title_cn": title_cn,
                "summary": summary,
                "authors": authors,
                "categories": cats,
                "url": f"https://arxiv.org/abs/{aid}"
            })
        return results

    def crawl_subcat_feed(self, date_from, date_to, subcat="cs.CL", max_pages=9):
        papers = {}
        major = subcat.split(".")[0].upper() if "." in subcat else "CS"
        print(f"[*] Crawling primary feed: subcat={subcat}, date={date_from} to {date_to}...")
        for page in range(1, max_pages + 1):
            url = f"https://www.arxivdaily.com/?date_from={date_from}&date_to={date_to}&major={major}&subcat={subcat}&sort=time&page={page}"
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                cards = self.parse_paper_cards(soup)
                if not cards:
                    break
                for p in cards:
                    papers[p["arxiv_id"]] = p
                print(f"    Page {page}: +{len(cards)} papers (Total: {len(papers)})")
                pagination = soup.find("nav", class_="pagination")
                if pagination and not pagination.find("a", string=re.compile(r"下一页")):
                    break
                time.sleep(0.5)
            except Exception as e:
                print(f"[!] Error fetching feed page {page}: {e}", file=sys.stderr)
                break
        return papers

    def search_query(self, query, date_from, date_to, max_pages=3):
        papers = {}
        for page in range(1, max_pages + 1):
            params = {
                "q": query,
                "search_in": "all",
                "date_from": date_from,
                "date_to": date_to,
                "sort": "time",
                "page": page
            }
            url = "https://www.arxivdaily.com/?" + requests.compat.urlencode(params)
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                cards = self.parse_paper_cards(soup)
                if not cards:
                    break
                for p in cards:
                    papers[p["arxiv_id"]] = p
                pagination = soup.find("nav", class_="pagination")
                if pagination and not pagination.find("a", string=re.compile(r"下一页")):
                    break
                time.sleep(0.4)
            except Exception as e:
                print(f"[!] Error searching query '{query}' p{page}: {e}", file=sys.stderr)
                break
        return papers


def fetch_arxiv_abstract(session, aid):
    url = f"https://arxiv.org/abs/{aid}"
    for retry in range(3):
        try:
            r = session.get(url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                abs_block = soup.find("blockquote", class_="abstract")
                if abs_block:
                    text = abs_block.get_text()
                    if text.startswith("Abstract:"):
                        text = text[9:].strip()
                    text = " ".join(text.split())
                    return text
            time.sleep(0.5)
        except Exception as e:
            time.sleep(1)
    return ""


def filter_and_group_papers(all_papers, domains_to_search, presets, limit_per_domain=15):
    grouped = {}

    for d_key in domains_to_search:
        preset_info = presets.get(d_key, {})
        d_name = preset_info.get("name", d_key)
        d_name_en = preset_info.get("name_en", d_key)
        filter_kws = preset_info.get("filter_keywords", [d_key.lower()])
        exclude_kws = preset_info.get("exclude_keywords", [])

        matched = []
        for aid, p in all_papers.items():
            text_corpus = (p["title_en"] + " " + p.get("title_cn", "") + " " + p.get("summary", "") + " " + " ".join(p.get("categories", []))).lower()
            
            # Check exclusions
            if any(ex in text_corpus for ex in exclude_kws):
                continue
            
            # Check inclusions
            match_score = 0
            for kw in filter_kws:
                kw_lower = kw.lower()
                if kw_lower in p["title_en"].lower():
                    match_score += 5
                elif kw_lower in p.get("summary", "").lower():
                    match_score += 2
                elif kw_lower in text_corpus:
                    match_score += 1
            
            if match_score > 0:
                matched.append((match_score, p))

        # Sort by match score descending
        matched.sort(key=lambda x: x[0], reverse=True)
        top_papers = [item[1] for item in matched[:limit_per_domain]]

        grouped[d_key] = {
            "domain_key": d_key,
            "domain_name": d_name,
            "domain_name_en": d_name_en,
            "count": len(top_papers),
            "papers": top_papers
        }

    return grouped


def main():
    parser = argparse.ArgumentParser(description="ArXiv & ArXivDaily Paper Searcher")
    parser.add_argument("--date", type=str, help="Target date YYYY-MM-DD")
    parser.add_argument("--date-from", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--date-to", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--domains", type=str, default="brain,rag,ie,foundation",
                        help="Comma-separated domain preset keys or custom domain names (e.g., 'brain,rag,ie,foundation' or 'eeg,agent')")
    parser.add_argument("--keywords", type=str, default="", help="Additional custom search queries comma-separated")
    parser.add_argument("--subcat", type=str, default="cs.CL", help="Primary arXiv subcategory feed (default: cs.CL)")
    parser.add_argument("--max-pages", type=int, default=9, help="Max pages of feed to crawl")
    parser.add_argument("--adv-pages", type=int, default=3, help="Max pages per search query")
    parser.add_argument("--fetch-abstracts", action="store_true", help="Fetch complete English abstract from arxiv.org")
    parser.add_argument("--limit-per-domain", type=int, default=15, help="Max papers per domain")
    parser.add_argument("--username", type=str, default=None, help="arXivDaily username (or via ARXIVDAILY_USERNAME env)")
    parser.add_argument("--password", type=str, default=None, help="arXivDaily password (or via ARXIVDAILY_PASSWORD env)")
    parser.add_argument("--output", type=str, default="", help="Path to output JSON")

    args = parser.parse_args()

    # Determine date range
    target_date = args.date or time.strftime("%Y-%m-%d")
    date_from = args.date_from or target_date
    date_to = args.date_to or target_date

    presets = load_presets()
    domain_keys = [d.strip() for d in args.domains.split(",") if d.strip()]

    # Collect all search queries
    search_queries = set()
    for d in domain_keys:
        if d in presets:
            for q in presets[d].get("search_queries", []):
                search_queries.add(q)
        else:
            # Custom keyword
            search_queries.add(d)

    if args.keywords:
        for kw in args.keywords.split(","):
            if kw.strip():
                search_queries.add(kw.strip())

    client = ArxivDailyClient(username=args.username, password=args.password)
    client.login()

    all_papers = {}

    # 1. Primary subcat crawl
    if args.subcat:
        feed_papers = client.crawl_subcat_feed(date_from, date_to, subcat=args.subcat, max_pages=args.max_pages)
        all_papers.update(feed_papers)

    # 2. Advanced search for all queries
    print(f"[*] Running advanced search for {len(search_queries)} queries...")
    for q in sorted(search_queries):
        q_papers = client.search_query(q, date_from, date_to, max_pages=args.adv_pages)
        added = 0
        for aid, p in q_papers.items():
            if aid not in all_papers:
                all_papers[aid] = p
                added += 1
        print(f"    Query '{q}': found {len(q_papers)} papers (+{added} new, total: {len(all_papers)})")

    print(f"[*] Total unique candidate papers scraped: {len(all_papers)}")

    # 3. Group and filter
    grouped_result = filter_and_group_papers(all_papers, domain_keys, presets, limit_per_domain=args.limit_per_domain)

    # 4. Fetch full abstracts if requested
    if args.fetch_abstracts:
        print("[*] Fetching original full abstracts from arxiv.org...")
        abs_session = requests.Session()
        abs_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        
        fetched_count = 0
        for d_key, d_data in grouped_result.items():
            for p in d_data["papers"]:
                if "abstract_en" not in p or not p["abstract_en"]:
                    p["abstract_en"] = fetch_arxiv_abstract(abs_session, p["arxiv_id"])
                    fetched_count += 1
                    time.sleep(0.2)
        print(f"[*] Fetched {fetched_count} full original abstracts.")

    total_curated = sum(d["count"] for d in grouped_result.values())
    output_data = {
        "date_from": date_from,
        "date_to": date_to,
        "total_unique_scraped": len(all_papers),
        "total_curated": total_curated,
        "domains": grouped_result
    }

    output_path = args.output
    if not output_path:
        output_path = os.path.join(os.getcwd(), f"arxiv_search_{date_from.replace('-', '')}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Search completed! Saved {total_curated} curated papers to {output_path}")


if __name__ == "__main__":
    main()
