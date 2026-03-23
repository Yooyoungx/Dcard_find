import time
import logging
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# ⚙️ 系統設定區
# ==========================================
FORUM_NAME = "tickets"
KEYWORDS = ["代購", "代買", "分攤", "負擔", "不拆賣",
            "分擔", "代搶", "微加價", "星巴克", "非原價", "飲料"]
CHECK_INTERVAL = 60

# 📱 Telegram 設定
TELEGRAM_BOT_TOKEN = "8322399509:AAF0tsylOIbn4BdRIniarNvarLUdOO4hgyk"
TELEGRAM_CHAT_ID = "-5259432856"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DcardTicketMonitorDP:
    def __init__(self):
        self.seen_post_ids = set()

        # 啟動 DrissionPage 瀏覽器設定
        co = ChromiumOptions()
        # 第一次測試建議設為 False (看得到畫面)，確定沒問題後可以改成 True (背景隱藏執行)
        co.headless(False)
        # 隱藏瀏覽器受到自動化控制的提示
        co.set_argument('--disable-blink-features=AutomationControlled')

        self.page = ChromiumPage(co)

    def send_telegram_alert(self, title: str, post_id: str, matched_keywords: list, snippet: str):
        """發送 Telegram 通知 (使用標準 requests)"""
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("請換成"):
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        message = (
            "🚨 **Dcard 票券板發現警示文章** 🚨\n\n"
            f"📌 **標題**: {title}\n"
            f"🔍 **觸發關鍵字**: {', '.join(matched_keywords)}\n"
            f"🔗 **連結**: https://www.dcard.tw/f/{FORUM_NAME}/p/{post_id}\n\n"
            f"📝 **內文片段**:\n{snippet}..."
        )

        try:
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=10)
            logger.info(f"📤 成功發送 Telegram 通知: {title}")
        except Exception as e:
            logger.error(f"❌ Telegram 發送失敗: {str(e)}")

    def fetch_api_via_browser(self, api_url: str):
        """🌟 核心絕招：讓瀏覽器自己去打 API，拿到最純淨的 JSON"""
        js_code = f"""
        return fetch('{api_url}')
            .then(res => res.json())
            .catch(err => null);
        """
        # run_js 會把瀏覽器 Console 執行後的 JSON 直接轉成 Python 字典！
        return self.page.run_js(js_code)

    def start(self):
        logger.info("🟢 Dcard 票券板監控系統 (DrissionPage 破盾版) 已啟動...")

        # 1. 先前往首頁，讓瀏覽器自動解開 Cloudflare 五秒盾
        logger.info("🔄 正在進入 Dcard 票券板，處理 Cloudflare 驗證...")
        self.page.get(f"https://www.dcard.tw/f/{FORUM_NAME}?tab=latest")

        # 等待網頁完全載入，確保 CF 驗證通過
        time.sleep(5)
        logger.info("✅ 成功進入 Dcard！準備開始 API 攔截。")

        # 2. 初始化快取
        init_url = f"/service/api/v2/forums/{FORUM_NAME}/posts?popular=false&limit=30"
        init_data = self.fetch_api_via_browser(init_url)

        if init_data:
            for p in init_data:
                self.seen_post_ids.add(str(p['id']))
            logger.info(f"✅ 初始化完成，緩存了 {len(self.seen_post_ids)} 篇文章。")
        else:
            logger.error("❌ 初始化 API 獲取失敗，請確認瀏覽器畫面是否卡在驗證碼。")

        # 3. 進入無窮迴圈監控
        while True:
            try:
                logger.info("🔍 掃描最新文章...")
                posts = self.fetch_api_via_browser(init_url)

                if not posts:
                    logger.warning("⚠️ 無法獲取文章，重新整理網頁以刷新 Cloudflare 授權...")
                    self.page.refresh()
                    time.sleep(5)
                    continue

                for post in posts:
                    post_id = str(post['id'])
                    title = post.get('title', '')

                    if post_id in self.seen_post_ids:
                        continue

                    self.seen_post_ids.add(post_id)

                    # 抓取完整內文
                    detail_url = f"/_api/posts/{post_id}"
                    post_detail = self.fetch_api_via_browser(detail_url)
                    content = post_detail.get(
                        'content', '') if post_detail else ''

                    full_text = f"{title}\n{content}"
                    matched_keywords = [
                        kw for kw in KEYWORDS if kw in full_text]

                    if matched_keywords:
                        logger.warning(
                            f"🎯 抓到了！文章: {title} | 關鍵字: {matched_keywords}")
                        snippet = content[:150].replace('\n', ' ')
                        self.send_telegram_alert(
                            title, post_id, matched_keywords, snippet)
                        time.sleep(1)

            except Exception as e:
                logger.error(f"❌ 掃描發生錯誤: {str(e)}")

            logger.info(f"💤 進入休眠，{CHECK_INTERVAL} 秒後下一次掃描...\n")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor = DcardTicketMonitorDP()
    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("🛑 系統接收到中斷指令，程式已安全停止。")
        monitor.page.quit()  # 安全關閉瀏覽器
