"""Tự tạo lại sitemap.xml từ các trang .html công khai trong thư mục web.

Trang KHÔNG đưa vào sitemap:
  - 404.html, tệp xác minh google*.html
  - thư mục bắt đầu bằng "_" hoặc "." (không được đăng lên web)
  - trang có <meta name="robots" content="noindex">
  - trang có thẻ canonical trỏ sang trang khác (vd: bản thử /a/)
  - trang nằm trong đường dẫn bị chặn ở robots.txt (quản trị, thanh toán...)

Cách dùng:
  python _cong-cu/tao-sitemap.py            # tạo lại sitemap.xml
  python _cong-cu/tao-sitemap.py --cai-hook # cài để tự chạy mỗi lần commit
"""
import os, re, subprocess, sys
from datetime import datetime, timezone

BASE = "https://phanphambao8x-sudo.github.io/avito-qua-bo-me/"
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chan_tu_robots():
    p = os.path.join(GOC, "robots.txt")
    if not os.path.exists(p):
        return []
    duong = []
    for dong in open(p, encoding="utf-8"):
        m = re.match(r"\s*Disallow:\s*(\S+)", dong)
        if m:
            duong.append(m.group(1))
    return duong


def ngay_sua(rel):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=GOC,
                             capture_output=True, text=True).stdout.strip()
        # Tệp đang sửa mà chưa commit thì lấy ngày hôm nay
        doi = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=GOC,
                             capture_output=True, text=True).stdout.strip()
        if out and not doi:
            return out
    except FileNotFoundError:
        pass
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def url_cua(rel):
    rel = rel.replace(os.sep, "/")
    if rel == "index.html":
        return BASE
    if rel.endswith("/index.html"):
        return BASE + rel[: -len("index.html")]
    return BASE + rel


def main():
    chan = chan_tu_robots()
    trang = []
    for thu_muc, con, tep in os.walk(GOC):
        con[:] = sorted(c for c in con if not c.startswith((".", "_")))
        for t in sorted(tep):
            if not t.endswith(".html") or t == "404.html" or re.fullmatch(r"google[0-9a-f]+\.html", t):
                continue
            rel = os.path.relpath(os.path.join(thu_muc, t), GOC)
            url = url_cua(rel)
            duong = "/" + url.split("://", 1)[1].split("/", 1)[1]
            if any(duong.startswith(c) for c in chan):
                continue
            html = open(os.path.join(thu_muc, t), encoding="utf-8").read()
            if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', html, re.I):
                continue
            m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html, re.I)
            if m and m.group(1) != url:
                continue
            trang.append((url, ngay_sua(rel)))

    trang.sort(key=lambda x: (x[0] != BASE, x[0]))
    dong = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, ngay in trang:
        dong += ["  <url>", f"    <loc>{url}</loc>", f"    <lastmod>{ngay}</lastmod>", "  </url>"]
    dong.append("</urlset>")
    moi = "\n".join(dong) + "\n"
    p = os.path.join(GOC, "sitemap.xml")
    cu = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    if moi != cu:
        open(p, "w", encoding="utf-8", newline="\n").write(moi)
    print(f"sitemap.xml: {len(trang)} trang" + ("" if moi != cu else " (không đổi)"))
    for url, ngay in trang:
        print("  ", ngay, url)


def cai_hook():
    hook = os.path.join(GOC, ".git", "hooks", "pre-commit")
    open(hook, "w", encoding="utf-8", newline="\n").write(
        "#!/bin/sh\n# Tự tạo lại sitemap.xml trước mỗi lần commit\n"
        "python _cong-cu/tao-sitemap.py >/dev/null && git add sitemap.xml\n")
    os.chmod(hook, 0o755)
    print("Đã cài: mỗi lần commit sẽ tự cập nhật sitemap.xml")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cai_hook() if "--cai-hook" in sys.argv else main()
