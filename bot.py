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
    list_url = board_info["url"]
    db_file = os.path.join(os.getcwd(), f"last_{name}.txt")
    
    page = await context.new_page()
    try:
        print(f"🔍 {name} 탭 스캔 시작...")
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        
        current_data = []
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        processed_count = 0
        for i in range(count):
            if processed_count >= 5: break
            
            # 제목 추출 및 내부 줄바꿈 제거
            raw_title = await rows.nth(i).inner_text()
            title_text = " ".join(raw_title.split()).strip()
            
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 상세 페이지 클릭하여 고유 URL 추출
            await rows.nth(i).click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1) # URL 확정 대기
            detail_url = page.url
            
            # [수정] 제목과 URL만 깔끔하게 한 줄로 저장 (본문 제외)
            if detail_url and "board" in detail_url:
                current_data.append(f"{title_text}||{detail_url}")
                print(f"    ✅ 수집: {title_text[:20]}")
                processed_count += 1
            
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(1)

        # 기존 파일 읽기
        old_data = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                # 빈 줄 제외하고 깔끔하게 읽기
                old_data = [line.strip() for line in f if line.strip()]

        # 비교 및 새 소식 알림
        for item in reversed(current_data):
            if item not in old_data:
                # item은 "제목||URL" 형태
                parts = item.split("||")
                if len(parts) == 2:
                    title, d_url = parts
                    if old_data: # 첫 실행이 아닐 때만 알림
                        msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                        requests.post(WEBHOOK_URL, json={"content": msg})

        # 파일 저장 (한 줄에 하나씩)
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 파일 저장 완료")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
