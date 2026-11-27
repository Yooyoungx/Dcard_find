import time
from curl_cffi import requests

LIST_URL = "https://www.dcard.tw/service/api/v2/forums/tickets/posts?popular=false&limit=5"
FORUM_URL = "https://www.dcard.tw/f/tickets?tab=latest"
POST_URL_TMPL = "https://www.dcard.tw/service/api/v2/posts/{post_id}"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": FORUM_URL,
}


def inspect_error(resp):
    print(f"  HTTP 狀態碼: {resp.status_code}")
    print(f"  Server: {resp.headers.get('server')} | CF-Ray: {resp.headers.get('cf-ray')}")
    print(f"  回應片段: {resp.text[:200]!r}")


def main():
    session = requests.Session(impersonate="chrome")

    print("=== [測試 1] 直連 tickets 板最新文章列表 API ===")
    resp = session.get(LIST_URL, headers=HEADERS, timeout=20)

    if resp.status_code != 200:
        print("❌ 直連列表失敗：")
        inspect_error(resp)

        print("\n=== [測試 1B] 先訪問看板主頁取 Cookie 後重試 ===")
        page_resp = session.get(FORUM_URL, timeout=20)
        print(f"  主頁狀態碼: {page_resp.status_code} | 取得 Cookies: {list(session.cookies.keys())}")
        time.sleep(2)
        resp = session.get(LIST_URL, headers=HEADERS, timeout=20)

    if resp.status_code != 200:
        print("❌ 重試列表仍失敗（Cloudflare 強制驗證，需改用瀏覽器核心或代理）：")
        inspect_error(resp)
        return

    posts = resp.json()
    print(f"✅ 列表抓取成功！共取得 {len(posts)} 篇文章：")
    for p in posts[:3]:
        print(f"  - ID: {p.get('id')} | 標題: {p.get('title')}")

    if not posts:
        return

    first_id = posts[0]["id"]
    print(f"\n=== [測試 2] 抓取單篇全文 API (ID: {first_id}) ===")
    time.sleep(2)
    detail_resp = session.get(POST_URL_TMPL.format(post_id=first_id), headers=HEADERS, timeout=20)

    if detail_resp.status_code != 200:
        print("❌ 單篇全文抓取失敗：")
        inspect_error(detail_resp)
        return

    detail = detail_resp.json()
    content = detail.get("content", "")
    print(f"✅ 全文抓取成功！內文總字數: {len(content)}")
    print(f"  內文前 60 字預覽: {content[:60]!r}")


if __name__ == "__main__":
    main()
