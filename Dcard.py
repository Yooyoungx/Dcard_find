import time
import logging
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# ==========================================
# ⚙️ 系統設定區
# ==========================================
FORUM_NAME = "tickets"
KEYWORDS = ["代購", "代買", "分攤", "負擔", "不拆賣",
            "分擔", "代搶", "微加價", "星巴克", "非原價", "飲料", "雙北地區"]
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
        co.headless(False)  # 必須看得到畫面才能穩定過盾
        co.set_argument('--disable-blink-features=AutomationControlled')

        self.page = ChromiumPage(co)
        # 如果你不想看到視窗一直閃，啟動後可以取消下面這行註釋來最小化
        # self.page.set.window.min()

    def send_telegram_alert(self, title: str, post_id: str, matched_keywords: list):
        """發送 Telegram 通知"""
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("請換成"):
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        # ⚠️ 拿掉原本的 * 和 _ 等 Markdown 符號，改用純文字，最安全！
        message = (
            "🚨 Dcard 票券板發現警示文章 🚨\n\n"
            f"📌 標題: {title}\n"
            f"🔍 觸發關鍵字: {', '.join(matched_keywords)}\n"
            f"🔗 連結: https://www.dcard.tw/f/{FORUM_NAME}/p/{post_id}\n\n"
            f"💡 已完成全文深度掃描，確認包含違規字眼。"
        )

        try:
            response = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                # ❌ 把這行註解掉或刪除，不要用 Markdown 解析
                # "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }, timeout=10)

            # ✨ 檢查 Telegram 伺服器的「真實回應」
            if response.status_code == 200:
                logger.info(f"📤 成功發送 Telegram 通知: {title}")
            else:
                # 如果 Telegram 拒絕發送，把真正的原因印在終端機上
                logger.error(
                    f"❌ Telegram 拒絕發送！狀態碼: {response.status_code} | 原因: {response.text}")

        except Exception as e:
            logger.error(f"❌ Telegram 發送發生網路連線錯誤: {str(e)}")

    def start(self):
        logger.info("🟢 Dcard 深度監控系統 (全內文掃描版) 已啟動...")

        # 1. 初始進入首頁
        logger.info("🔄 正在進入 Dcard 票券板...")
        self.page.get(f"https://www.dcard.tw/f/{FORUM_NAME}?tab=latest")
        time.sleep(5)

        # 2. 初始化快取：紀錄目前畫面上已有的文章，避免重開程式時洗版
        initial_articles = self.page.eles('tag:article')
        for art in initial_articles:
            try:
                link_ele = art.ele('@aria-label=查看全文', timeout=1)
                if link_ele:
                    post_id = link_ele.link.split('/p/')[-1].split('?')[0]
                    self.seen_post_ids.add(post_id)
            except:
                pass
        logger.info(f"✅ 初始化完成，目前忽略前 {len(self.seen_post_ids)} 篇文章。")

        # 3. 進入無窮迴圈監控
        while True:
            try:
                logger.info("🔄 重新整理網頁，檢查最新文章...")
                self.page.refresh()
                time.sleep(5)  # 等待頁面載入

                articles = self.page.eles('tag:article')

                for art in articles:
                    try:
                        # 準確抓取文章進入連結，避開頭像連結
                        link_ele = art.ele('@aria-label=查看全文', timeout=1)
                        if not link_ele:
                            continue

                        post_url = link_ele.link
                        post_id = post_url.split('/p/')[-1].split('?')[0]

                        # 如果是看過的 ID 就跳過
                        if post_id in self.seen_post_ids:
                            continue

                        # 🌟 發現新文章！
                        self.seen_post_ids.add(post_id)
                        title_ele = art.ele('tag:h2', timeout=1)
                        title = title_ele.text if title_ele else "新文章"

                        logger.info(f"🆕 發現新文章: {title}，深度掃描中...")

                        # 🚀 深度掃描動作：在新標籤頁打開文章，獲取 100% 完整內文
                        new_tab = self.page.new_tab(post_url)
                        time.sleep(4)  # 給內文充足的載入時間

                        # 抓取整頁文字 (InnerText 包括所有文字內容，不受預覽限制)
                        full_content = new_tab.run_js(
                            "return document.body.innerText")

                        # 在全文中檢查關鍵字
                        matched_keywords = [
                            kw for kw in KEYWORDS if kw in full_content]

                        if matched_keywords:
                            logger.warning(f"🎯 命中！全文包含關鍵字: {matched_keywords}")
                            self.send_telegram_alert(
                                title, post_id, matched_keywords)

                        # 檢查完畢，關閉分頁回到列表
                        new_tab.close()
                        time.sleep(1)

                    except Exception as inner_e:
                        logger.error(f"⚠️ 處理單篇文章時發生錯誤: {inner_e}")
                        continue

            except Exception as e:
                logger.error(f"❌ 監控迴圈發生錯誤: {str(e)}")

            logger.info(f"💤 進入休眠，{CHECK_INTERVAL} 秒後下一次掃描...\n")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor = DcardTicketMonitorDP()
    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("🛑 系統接收到中斷指令，程式已安全停止。")
        monitor.page.quit()
