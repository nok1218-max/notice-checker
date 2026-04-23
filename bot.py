import os
import asyncio
from playwright.async_api import async_playwright
import requests

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"

# 감시할 게시판 리스트 (이름과 URL)
TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

async def check_board(context, board_info):
    name = board_info["name"]
    url = board_info["url"]
    db_file = f"last_{name}.txt" # 게시판별로 저장 파일 분리
    
    page = await context.new_page()
    try:
        print(f"🔍 {name} 확인 중...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)

        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()
        
        latest_title = ""
        for i in range(count):
            text = await rows.nth(i).inner_text()
            text = " ".join(text.split()).strip()
            
            # 헤더 및 불필요한 텍스트 제외
            if text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(text) < 2:
                continue
            
            latest_title = text
            break

        if not latest_title:
            print(f"❌ {name} 본문을 찾을 수 없습니다.")
            return

        # 이전 기록 읽기
        last_title = ""
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                last_title = f.read().strip()

        if latest_title != last_title:
            print(f"✅ {name} 새 글 발견: {latest_title}")
            
            payload = {
                "embeds": [{
                    "title": f"📢 메이플랜드 [{name}]",
                    "description": latest_title,
                    "url": url,
                    "color": 16753920 if name == "공지사항" else (3447003 if name == "이벤트" else 10181046)
                }]
            }
            requests.post(WEBHOOK_URL, json=payload)
            
            with open(db_file, "w", encoding="utf-8") as f:
                f.write(latest_title)
        else:
            print(f"😴 {name} 업데이트 없음.")

    except Exception as e:
        print(f"⚠️ {name} 오류: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        
        # 모든 게시판 순차적으로 확인
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(2) # 차단 방지를 위한 짧은 휴식
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
