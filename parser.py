#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import os
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

DEFAULT_OUT = "willhaben_listings.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_url_from_env() -> str:
    """
    Build the Willhaben search URL from environment variables.

    Returns:
        Complete URL with all query parameters
    """
    base_url = os.getenv("BASE_URL", "https://www.willhaben.at")
    listing_path = os.getenv("LISTING_PATH", "/iad/immobilien/mietwohnungen/mietwohnung-angebote")

    # Build query parameters
    params = {}

    # Single value params
    if rows := os.getenv("ROWS"):
        params["rows"] = rows
    if sort := os.getenv("SORT"):
        params["sort"] = sort
    if is_nav := os.getenv("IS_NAVIGATION"):
        params["isNavigation"] = is_nav
    if sf_id := os.getenv("SF_ID"):
        params["sfId"] = sf_id
    if page := os.getenv("PAGE"):
        params["page"] = page
    if price_to := os.getenv("PRICE_TO"):
        params["PRICE_TO"] = price_to
    if estate_size := os.getenv("ESTATE_SIZE_FROM"):
        params["ESTATE_SIZE/LIVING_AREA_FROM"] = estate_size

    # Multi-value params (comma-separated in .env)
    if area_ids := os.getenv("AREA_IDS"):
        params["areaId"] = area_ids.split(",")
    if room_buckets := os.getenv("NO_OF_ROOMS_BUCKETS"):
        params["NO_OF_ROOMS_BUCKET"] = room_buckets.split(",")
    if property_types := os.getenv("PROPERTY_TYPES"):
        params["PROPERTY_TYPE"] = property_types.split(",")

    # Build URL
    query_string = urlencode(params, doseq=True)
    return f"{base_url}{listing_path}?{query_string}"


def set_rows_param(url: str, rows: int | None) -> str:
    """
Вставляет/обновляет query-параметр rows.
Если rows=None: если rows уже есть в URL — оставляем как есть, иначе ставим 10000.
Если rows задан — принудительно выставляем его.
    """
    pr = urlparse(url)
    q = parse_qs(pr.query, keep_blank_values=True)

    if rows is None:
        if "rows" not in q:
            q["rows"] = [str(DEFAULT_ROWS)]
    else:
        q["rows"] = [str(rows)]

    new_query = urlencode(q, doseq=True)
    return urlunparse((pr.scheme, pr.netloc, pr.path, pr.params, new_query, pr.fragment))


def fetch(url: str) -> str:
    with requests.Session() as s:
        s.headers.update(HEADERS)
        resp = s.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def extract_id_from_href(href: str) -> str | None:
    # Пытаемся вытащить id из параметра ?adId=123456789
    m = re.search(r"[?&]adId=(\d+)", href)
    if m:
        return m.group(1)

    # Иногда id в конце пути /.../123456789
    m = re.search(r"/(\d{6,})/?$", href)
    if m:
        return m.group(1)

    return None


def extract_price(text: str) -> str | None:
    # Первая сумма с символом евро
    m = re.search(r"\b[\d.\s]+(?:,\d{2})?\s*€", text)
    if m:
        return normalize_space(m.group(0))
    return None


def extract_size(text: str) -> str | None:
    # Первая площадь с м²
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*m²", text, flags=re.IGNORECASE)
    if m:
        # Возвращаем как "XX m²"
        return f"{m.group(1).replace(',', '.') } m²"
    return None


def guess_address(lines: list[str]) -> str | None:
    """
Ищем строку, похожую на адрес/локацию.
Эвристики: содержит "Wien", "Bezirk", названия земель.
    """
    patterns = [
        r"\bWien\b",
        r"\bBezirk\b",
        r"\bNiederösterreich\b",
        r"\bOberösterreich\b",
        r"\bSteiermark\b",
        r"\bBurgenland\b",
        r"\bSalzburg\b",
        r"\bTirol\b",
        r"\bVorarlberg\b",
        r"\bKärnten\b",
    ]
    for ln in lines:
        if any(re.search(pat, ln, flags=re.IGNORECASE) for pat in patterns):
            return ln
    # fallback — просто вторая или третья информативная строка
    for ln in lines:
        if len(ln) >= 6 and not re.search(r"€|m²|Zimmer|Gesamtmiete|Kaution|Betriebskosten", ln, re.I):
            return ln
    return None


def extract_by_card(container, base_url: str) -> dict | None:
    """
Извлекаем данные внутри карточки.
    """
    # Ссылка и заголовок
    a = container.find("a", href=True)
    if not a:
        return None
    href = a["href"]
    link = urljoin(base_url, href)
    listing_name = normalize_space(a.get_text(" ", strip=True))

    # Полный текст карточки строками
    text = normalize_space(container.get_text(" ", strip=True))
    lines = [normalize_space(x) for x in re.split(r"[•\n\r]+| {2,}", text) if normalize_space(x)]

    price = extract_price(text)
    apart_size = extract_size(text)

    # Адрес: пробы через явные классы
    address = None
    for cls_pat in [r"address", r"location", r"region"]:
        el = container.find(True, class_=re.compile(cls_pat, re.I))
        if el:
            address = normalize_space(el.get_text(" ", strip=True))
            break
    if not address:
        address = guess_address(lines)

    # ID: из href или из data-атрибутов
    ad_id = extract_id_from_href(href)
    if not ad_id:
        for attr in ["data-id", "data-adid", "data-item-id", "data-tracking-id"]:
            if container.has_attr(attr):
                ad_id = container.get(attr)
                break

    return {
        "id": ad_id or "",
        "listing_name": listing_name,
        "price": price or "",
        "address": address or "",
        "apart_size": apart_size or "",
        "link": link,
    }


def extract_from_jsonld(soup: BeautifulSoup, base_url: str) -> dict[str, dict]:
    """
Пробуем достать имена/ссылки из JSON-LD (ItemList/ListItem).
Возвращаем словарь по ссылке.
    """
    items_by_link = {}
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for sc in scripts:
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue

        payloads = data if isinstance(data, list) else [data]
        for d in payloads:
            if not isinstance(d, dict):
                continue
            if d.get("@type") == "ItemList" and "itemListElement" in d:
                for li in d["itemListElement"]:
                    # варианты: {"@type":"ListItem","position":1,"url":"...","name":"..."}
                    # или {"@type":"ListItem","item":{"@id":"...","name":"...","url":"..."}}
                    url = None
                    name = None
                    if isinstance(li, dict):
                        if "url" in li:
                            url = li["url"]
                        item = li.get("item")
                        if isinstance(item, dict):
                            url = url or item.get("url") or item.get("@id")
                            name = item.get("name")
                        name = name or li.get("name")
                    if url:
                        full = urljoin(base_url, url)
                        items_by_link[full] = {"listing_name": normalize_space(name or "")}
    return items_by_link


def parse_list_page(html: str, base_url: str = "https://www.willhaben.at") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Попытка укрепить title по JSON-LD (если есть)
    jsonld_titles = extract_from_jsonld(soup, base_url)

    # Находим все карточки по якорям со ссылками на детали
    anchors = soup.find_all("a", href=re.compile(r"^/iad/immobilien/(?:d/|.*\?adId=)"))
    seen_links = set()
    results = []

    for a in anchors:
        link = urljoin(base_url, a.get("href", ""))
        if link in seen_links:
            continue
        seen_links.add(link)

        # Ищем разумный контейнер карточки
        container = (
            a.find_parent("article")
            or a.find_parent("li")
            or a.find_parent("div", class_=re.compile(r"(result|card|box|tile)", re.I))
            or a.parent
        )
        item = extract_by_card(container, base_url)
        if not item:
            continue

        # Если name пустоват — подставим из JSON-LD
        if (not item.get("listing_name")) and (link in jsonld_titles):
            item["listing_name"] = jsonld_titles[link].get("listing_name", "")

        results.append(item)

    # Фильтруем мусор: хотя бы ссылка и (id или title)
    filtered = [r for r in results if r.get("link") and (r.get("id") or r.get("listing_name"))]
    # Дедуп по ссылке
    uniq = {}
    for r in filtered:
        uniq[r["link"]] = r
    return list(uniq.values())


def write_csv(rows: list[dict], out_path: str):
    fields = ["id", "listing_name", "price", "address", "apart_size", "link"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Build default URL from environment variables
    default_url = build_url_from_env()

    ap = argparse.ArgumentParser(description="Parse Willhaben list page into CSV.")
    ap.add_argument("--url", default=default_url, help="URL страницы списка Willhaben")
    ap.add_argument("--rows", type=int, default=None, help="Значение параметра &rows= (переопределяет значение из .env)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="Путь к выходному CSV")
    args = ap.parse_args()

    url = set_rows_param(args.url, args.rows)
    html = fetch(url)
    items = parse_list_page(html)
    write_csv(items, args.out)
    print(f"Parsed {len(items)} listings -> {args.out}")


if __name__ == "__main__":
    main()
    