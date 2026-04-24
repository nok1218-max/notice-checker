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
        # 목록 페이지만 읽으면 되므로 로딩이 훨씬 빠릅니다.
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        
        current_data = []
        # 목록 요소가 뜰 때까지 대기
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        # 목록에서 제목과 링크 추출 (상세 페이지 진입 안 함)
        # 각 행(row)을 돌며 제목과 해당 글의 고유 경로를 찾습니다.
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()

        processed_count = 0
        for i in range(count):
            if processed_count >= 5: break
            
            title_text = (await rows.nth(i).inner_text()).strip()
            
            # 필터링: 메뉴명이나 무의미한 텍스트 제외
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 클릭 대신 현재 요소의 상위 a태그 등에서 URL을 가져오거나, 
            # 메이플랜드 구조상 클릭 후 URL을 따오는 방식 유지
            await rows.nth(i).click()
            await page.wait_for_load_state("domcontentloaded")
            detail_url = page.url
            
            # 제목과 URL만 결합하여 데이터 생성
            current_data.append(f"{title_text}||{detail_url}")
            print(f"    ✅ 확인: {title_text[:20]}")
            processed_count += 1
            
            # 다시 목록으로 돌아가기
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(1)

        # 비교 및 알림 로직
        old_data = []
        is_first_run = not os.path.exists(db_file)
        if not is_first_run:
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 2: continue
                title, d_url = parts
                
                # 새 글이 올라왔을 때만 알림 전송
                if not is_first_run:
                    msg = f"**[{name}] 새로운 소식이 등록되었습니다!**\n제목: {title}\n링크: {d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})

        # 파일 저장
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 업데이트 완료")

    except Exception as e:
        print(f"❌ {name} 오류 발생: {e}")
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
