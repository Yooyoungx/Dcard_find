import asyncio
import nodriver as uc

FORUM_URL = "https://www.dcard.tw/f/tickets?tab=latest"
LIST_API_URL = "https://www.dcard.tw/service/api/v2/forums/tickets/posts?popular=false&limit=3"


async def main():
    browser = await uc.start(
        headless=False,
        sandbox=False,
        browser_args=[
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
            "--lang=zh-TW",
        ],
    )

    try:
        print("=== [測試 1] 真實 Chrome 開啟看板主頁 ===")
        page = await browser.get(FORUM_URL)
        await asyncio.sleep(8)

        title = await page.evaluate("document.title")
        print(f"初次網頁標題: {title!r}")

        # 若遇到 Cloudflare 轉圈驗證，多等 10 秒看能否自動通過
        if title and any(k in title for k in ["Just a moment", "請稍候", "Attention"]):
            print("偵測到 Cloudflare 頁面，等待 10 秒後重檢...")
            await asyncio.sleep(10)
            title = await page.evaluate("document.title")
            print(f"等待後標題: {title!r}")

        body_preview = await page.evaluate(
            "document.body ? document.body.innerText.slice(0, 250) : ''"
        )
        print(f"頁面文字預覽:\n{body_preview}\n")

        links = await page.evaluate(
            """Array.from(document.querySelectorAll('a[href*="/f/tickets/p/"]'))
               .slice(0, 5)
               .map(a => a.innerText.replace(/\\s+/g, ' ').trim() + ' -> ' + a.getAttribute('href'))
               .join('\\n')"""
        )
        if links:
            print(f"✅ DOM 成功抓到看板文章連結:\n{links}\n")
        else:
            print("❌ DOM 未發現文章連結\n")

        print("=== [測試 2] 同個瀏覽器 Session 直接讀取列表 API ===")
        await page.get(LIST_API_URL)
        await asyncio.sleep(3)
        api_text = await page.evaluate(
            "document.body ? document.body.innerText.slice(0, 400) : ''"
        )
        print(f"API 回應前 400 字:\n{api_text}")

    finally:
        browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
