import os
import asyncio
from playwright.async_api import async_playwright
import requests

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"

TARGETS = [
    {"name": "공지사항", "url": "https://maple.land/board/notices"},
    {"name": "이벤트", "url": "https://maple.land/board/events"},
    {"name": "개발일지", "url": "https://maple.land/board/devlog"}
]

async def check_board(context, board_info):
    name = board_info["name"]
    url = board_info["url"]
    db_file = f"last_{name}.txt"
    
    page = await context.new_page()
    try:
        print(f"🔍 {name} 확인 중...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)

        # 현재 페이지의 공지사항들 가져오기
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()
        
        current_notices = []
        for i in range(count):
            text = await rows.nth(i).inner_text()
            text = " ".join(text.split()).strip()
            
            # 필터링
            if text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(text) < 3:
                continue
            
            current_notices.append(text)
            if len(current_notices) >= 5: # 최신 5개까지만 수집
                break

        if not current_notices:
            print(f"❌ {name}에서 공지를 찾지 못했습니다.")
            return

        # 이전 기록(최대 5개) 읽기
        old_notices = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_notices = [line.strip() for line in f.readlines() if line.strip()]

        # 새 공지 확인 (기존 목록에 없는 것들만 발송)
        new_found = False
        for notice in reversed(current_notices): # 오래된 순서대로 알림 보내기 위해 반전
            if notice not in old_notices:
                print(f"✅ {name} 새 소식 발견: {notice}")
                
                color = 16753920 if name == "공지사항" else (3447003 if name == "이벤트" else 10181046)
                payload = {
                    "embeds": [{
                        "title": f"📢 메이플랜드 [{name}]",
                        "description": notice,
                        "url": url,
                        "color": color
                    }]
                }
                requests.post(WEBHOOK_URL, json=payload)
                new_found = True

        # 새 공지가 있었다면 파일 업데이트
        if new_found:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_notices))
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
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
