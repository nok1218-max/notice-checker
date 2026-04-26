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
        
        # (제목, URL) 튜플을 담을 리스트
        current_data_with_url = []
        # 파일 저장용 제목 리스트
        current_titles = []
        
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        processed_count = 0
        for i in range(count):
            if processed_count >= 5: break
            
            # 제목 추출 및 전처리
            raw_title = await rows.nth(i).inner_text()
            title_text = " ".join(raw_title.split()).strip()
            
            # [수정] 제목 끝의 'N' 표시 제거
            if title_text.endswith(' N'):
                title_text = title_text[:-2].strip()
            
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 상세 페이지로 이동하여 URL 획득
            await rows.nth(i).click()
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(0.5) 
            detail_url = page.url
            
            # 데이터 수집 (알림용에는 URL 포함, 저장용에는 제목만)
            if detail_url and "board" in detail_url:
                current_data_with_url.append((title_text, detail_url))
                current_titles.append(title_text)
                print(f"    ✅ 수집: {title_text[:20]}")
                processed_count += 1
            
            # 목록으로 복귀
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(0.5)

        # 기존 파일 읽기 (제목 리스트)
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        # 비교 및 알림 (제목만으로 중복 체크)
        for title, d_url in reversed(current_data_with_url):
            if title not in old_titles:
                if old_titles: # 첫 실행이 아닐 때만 알림
                    msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})

        # 파일 저장 (제목만 저장하여 URL/N 유무로 인한 중복 발생 방지)
        if current_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_titles))
            print(f"💾 {name} 파일 저장 완료 (제목만)")

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
