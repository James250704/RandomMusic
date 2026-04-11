import time
import random
import hashlib
import asyncio
import httpx
from DrissionPage import ChromiumPage, ChromiumOptions

# === 配置區 ===
BATCH_SIZE = 40

def get_sapisid_hash(sapisid, origin="https://music.youtube.com"):
    timestamp = int(time.time())
    msg = f"{timestamp} {sapisid} {origin}"
    sha1_hash = hashlib.sha1(msg.encode()).hexdigest()
    return f"SAPISIDHASH {timestamp}_{sha1_hash}"

async def main():
    PLAYLIST_ID = input("請輸入播放清單 ID：")
    options = ChromiumOptions()
    options.headless = True
    # 3. 額外優化：防止被偵測 (Headless 必加)
    options.set_argument('--no-sandbox')  # Linux/Docker 環境必備
    options.set_argument('--disable-gpu') # 減少資源佔用
    options.set_argument('--incognito')   # 隱身模式 (可選，但有助於乾淨的環境)
    
    # 強烈建議：即使是 headless，也要手動設置 UA，模擬真實系統
    options.set_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")
    page = ChromiumPage(options)
    page.get(f"https://music.youtube.com/playlist?list={PLAYLIST_ID}")
    print(f"正在載入播放清單...")
    time.sleep(4)

    # 1. 捲動以加載所有歌曲
    last_count = 0
    while True:
        # 捲動到底部
        page.scroll.to_bottom()
        time.sleep(2)  # 等待網絡加載
        
        # 檢查當前抓到了多少首
        current_count = page.run_js("return document.querySelectorAll('ytmusic-responsive-list-item-renderer').length")
        print(f"  已載入 {current_count} 首歌...")
        
        if current_count == last_count:
            # 嘗試再捲一次確認真的到底了
            page.scroll.to_bottom()
            time.sleep(2)
            if page.run_js("return document.querySelectorAll('ytmusic-responsive-list-item-renderer').length") == last_count:
                break
        last_count = current_count

    # 2. 透過 JS 直接從 DOM 提取所有歌曲的 setVideoId (最準確的方法)
    print("正在提取歌曲 ID 資料...")
    songs = page.run_js("""
        return Array.from(document.querySelectorAll('ytmusic-responsive-list-item-renderer')).map(el => {
            const title = el.querySelector('.title')?.innerText || '?';
            // YouTube Music 的資料通常存在元素對象的屬性中
            const setVideoId = el.data?.playlistItemData?.playlistSetVideoId || 
                               el.querySelector('yt-checkbox-renderer')?.getAttribute('video-id'); 
            return { title, setVideoId };
        }).filter(s => s.setVideoId);
    """)

    if not songs:
        print("❌ 找不到歌曲，請檢查權限或頁面結構")
        return

    print(f"✅ 成功獲取全部 {len(songs)} 首歌")

    # 3. 隨機打亂
    target_order = songs[:]
    random.shuffle(target_order)
    
    # 4. 準備授權環境
    raw_cookies = page.cookies()
    cookies_dict = {c['name']: c['value'] for c in raw_cookies}
    sapisid = cookies_dict.get('__Secure-3PAPISID') or cookies_dict.get('SAPISID')
    inner_context = page.run_js("return ytcfg.get('INNERTUBE_CONTEXT')")
    client_version = page.run_js("return ytcfg.get('INNERTUBE_CLIENT_VERSION')")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Authuser": "0",
        "X-Origin": "https://music.youtube.com",
        "X-Youtube-Client-Name": "67",
        "X-Youtube-Client-Version": client_version,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "Cookie": "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
    }

    # 5. 構造批量 Actions (逆序鏈式置頂)
    reversed_target = target_order[::-1]
    all_actions = []
    for i in range(len(reversed_target) - 1):
        all_actions.append({
            "action": "ACTION_MOVE_VIDEO_BEFORE",
            "setVideoId": reversed_target[i+1]['setVideoId'],
            "movedSetVideoId": reversed_target[i]['setVideoId']
        })

    chunks = [all_actions[i:i + BATCH_SIZE] for i in range(0, len(all_actions), BATCH_SIZE)]
    print(f"\n總共 {len(all_actions)} 個動作，分成 {len(chunks)} 個封包發送...")

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, read=30.0) # 讀取時間設長一點

    async with httpx.AsyncClient(http2=True, timeout=timeout, limits=limits) as client:
        for idx, chunk in enumerate(chunks):
            # ... 更新 Authorization ...
            headers["Authorization"] = get_sapisid_hash(sapisid)
            
            payload = {
                "context": inner_context,
                "playlistId": PLAYLIST_ID,
                "actions": chunk
            }

            try:
                print(f"  正在發送封包 {idx+1}/{len(chunks)} (包含 {len(chunk)} 個動作)...")
                resp = await client.post(
                    "https://music.youtube.com/youtubei/v1/browse/edit_playlist",
                    json=payload,
                    headers=headers
                )

                if resp.status_code == 200:
                    print(f"  ✅ 封包 {idx+1} 發送成功")
                elif resp.status_code == 409:
                    print(f"  ⏳ 封包 {idx+1} 發生 409 衝突，等待後重試...")
                    await asyncio.sleep(3.0)
                    # 可以在這裡寫簡單的重試邏輯
                else:
                    print(f"  ❌ 封包 {idx+1} 失敗 {resp.status_code}: {resp.text[:100]}")
            
            except httpx.ReadTimeout:
                print(f"  ⚠️ 封包 {idx+1} 讀取超時，但伺服器可能正在背景處理，等待 5 秒後繼續...")
                await asyncio.sleep(5.0)
            except Exception as e:
                print(f"  ❌ 發生意外錯誤: {e}")

            # 3. 批量動作後一定要留時間給資料庫更新索引
            await asyncio.sleep(1.5)

    print("\n✅ 全體任務處理完畢。")

if __name__ == "__main__":
    asyncio.run(main())