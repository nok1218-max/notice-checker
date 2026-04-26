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
    
    # 각 게시판마다 개별 페이지(탭) 생성하여 병렬 처리
    page = await context.new_page()
    try:
        print(f"🔍 {name} 스캔 시작...")
        # wait_until을 "domcontentloaded"로 낮추어 로딩 속도 향상
        await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
        
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=15000)
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        current_data_with_url = []
        current_titles = []
        processed_count = 0

        for i in range(count):
            if processed_count >= 5: break
            
            row = rows.nth(i)
            raw_title = await row.inner_text()
            title_text = " ".join(raw_title.split()).strip()
            
            if title_text.endswith(' N'):
                title_text = title_text[:-2].strip()
            
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 클릭 후 상세 페이지 URL 획득 (가장 확실한 방법)
            await row.click()
            # 네트워크가 완전히 멈출 때까지 기다리지 않고 URL만 바뀌면 즉시 수집
            await page.wait_for_load_state("commit") 
            detail_url = page.url
            
            if detail_url and "board" in detail_url:
                current_data_with_url.append((title_text, detail_url))
                current_titles.append(title_text)
                processed_count += 1
            
            # 목록으로 빠르게 복귀
            await page.go_back(wait_until="domcontentloaded")

        # 데이터 비교 및 알림 (이전과 동일)
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        for title, d_url in reversed(current_data_with_url):
            if title not in old_titles:
                if old_titles:
                    msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})

        if current_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_titles))
            print(f"💾 {name} 완료")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 세션 재사용
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        
        # [핵심] 모든 타겟을 동시에 실행
        tasks = [check_board(context, target) for target in TARGETS]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
