import asyncio
import os
import shutil
import subprocess
import nodriver as uc

FORUM_URL = "https://www.dcard.tw/f/tickets?tab=latest"
LIST_API_URL = "https://www.dcard.tw/service/api/v2/forums/tickets/posts?popular=false&limit=3"


def diagnose_chrome(chrome_path: str):
    print("\n=== [診斷] 檢查 Chrome 底層錯誤訊息 ===")
    print(f"DISPLAY={os.environ.get('DISPLAY')!r} | Chrome 路徑={chrome_path!r}")
    if not chrome_path:
        print("找不到 Chrome 執行檔")
        return

    ver = subprocess.run([chrome_path, "--version"], capture_output=True, text=True)
    print(f"Chrome 版本: {ver.stdout.strip()} {ver.stderr.strip()}")

    try:
        proc = subprocess.run(
            [
                chrome_path,
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--remote-debugging-port=9222",
                "about:blank",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print(f"Chrome 提前退出 (code={proc.returncode})")
        print(f"stderr:\n{proc.stderr[:1200]}")
    except subprocess.TimeoutExpired as e:
        print("Chrome 本身可正常常駐 5 秒（代表不是閃退，而是 nodriver 連線超時）")
        if e.stderr:
            err = e.stderr.decode("utf-8", errors="ignore") if isinstance(e.stderr, bytes) else e.stderr
            print(f"stderr 片段:\n{err[:800]}")


async def start_browser(chrome_path: str):
    args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,800",
        "--lang=zh-TW",
    ]

    last_err = None
    for attempt in range(1, 3):
        try:
            print(f"啟動瀏覽器（第 {attempt} 次嘗試）...")
            return await uc.start(
                browser_executable_path=chrome_path,
                headless=False,
                sandbox=False,
                browser_args=args,
            )
        except Exception as e:
            last_err = e
            print(f"第 {attempt} 次啟動失敗: {e}")
            await asyncio.sleep(2)

    diagnose_chrome(chrome_path)
    raise last_err


async def main():
    chrome_path = (
        shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )

    browser = await start_browser(chrome_path)

    try:
        print("\n=== [測試 1] 真實 Chrome 開啟看板主頁 ===")
        page = await browser.get(FORUM_URL)
        await asyncio.sleep(8)

        title = await page.evaluate("document.title")
        print(f"初次網頁標題: {title!r}")

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
            """
