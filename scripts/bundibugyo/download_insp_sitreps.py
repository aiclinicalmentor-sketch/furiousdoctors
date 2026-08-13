import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


API_URL = "https://insp.cd/wp-json/wp/v2/posts?categories=308&per_page=100&orderby=date&order=desc"
REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / ".bundibugyo_work"
PDF_DIR = WORK_DIR / "DRC SitReps"
MANIFEST = WORK_DIR / "downloaded_sitreps_manifest.json"


def fetch_json(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_bytes(url):
    request = Request(ascii_url(url), headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=90) as response:
        return response.read()


def ascii_url(url):
    parsed = urlparse(url)
    path = quote(unquote(parsed.path), safe="/%")
    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))


def decode_pdfemb(value):
    padded = value + "=" * (-len(value) % 4)
    payload = base64.urlsafe_b64decode(padded).decode("utf-8")
    return json.loads(payload)


def pdf_urls_from_content(content):
    urls = []
    for encoded in re.findall(r"pdfemb-data=([^\"'&]+)", html.unescape(content)):
        try:
            data = decode_pdfemb(encoded)
        except Exception:
            continue
        url = data.get("url")
        if url and url.lower().endswith(".pdf"):
            urls.append(url)

    for url in re.findall(r"https?://[^\"'<> ]+?\.pdf", html.unescape(content)):
        urls.append(url.replace("\\/", "/"))

    return list(dict.fromkeys(urls))


def filename_from_url(url):
    name = unquote(Path(urlparse(url).path).name)
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    posts = fetch_json(API_URL)
    downloaded = []
    skipped = []
    failed = []

    for post in posts:
        title = html.unescape(post.get("title", {}).get("rendered", "")).strip()
        content = post.get("content", {}).get("rendered", "")
        for url in pdf_urls_from_content(content):
            filename = filename_from_url(url)
            target = PDF_DIR / filename
            record = {"title": title, "post": post.get("link"), "pdf": url, "file": filename}
            if target.exists() and target.stat().st_size > 0:
                skipped.append(record)
                continue
            try:
                data = fetch_bytes(url)
            except (HTTPError, URLError, TimeoutError) as exc:
                record["error"] = str(exc)
                failed.append(record)
                print(f"failed {filename} from {title}: {exc}")
                continue
            target.write_bytes(data)
            downloaded.append(record)

    manifest = {
        "source_api": API_URL,
        "downloaded": downloaded,
        "skipped_existing": skipped,
        "failed": failed,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"downloaded={len(downloaded)} skipped_existing={len(skipped)} failed={len(failed)} manifest={MANIFEST}")
    for record in downloaded:
        print(f"downloaded {record['file']} from {record['title']}")


if __name__ == "__main__":
    main()
