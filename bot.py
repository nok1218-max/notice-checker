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
        print(f"🔍 {name} 탭 확인 중...")
        # 1. 목록 페이지 접속
        await page.goto(list_url, wait_until="commit", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        current_data = [] 
        
        for i in range(5): # 상위 5개 타겟
            # 매번 요소를 새로 찾아서 인덱스 에러 방지
            rows = page.locator('div.min-w-0.flex-1')
            if i >= await rows.count(): break
            
            title_text = await rows.nth(i).inner_text()
            title_text = " ".join(title_text.split()).strip()
            
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 게시글 클릭
            print(f"    └ [{i+1}/5] 상세 내용 확인: {title_text[:15]}...")
            await rows.nth(i).click()
            
            try:
                # 상세 페이지 로딩 대기 (prose 클래스 또는 다른 본문 요소)
                await page.wait_for_load_state("networkidle")
                detail_url = page.url 
                
                # 본문 요소가 나타날 때까지 대기
                content_element = page.locator('div.prose')
                await content_element.wait_for(state="visible", timeout=15000)
                
                full_content = await content_element.inner_text()
                clean_content = " ".join(full_content.split()).strip()[:1000]
                current_data.append(f"{title_text}||{clean_content}||{detail_url}")
                
            except Exception as e:
                print(f"      ⚠️ 본문 읽기 실패 ({title_text[:10]}): {e}")
            
            # 목록으로 돌아가기
            await page.go_back()
            # 목록 요소가 다시 나타날 때까지 확실히 대기
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
            await asyncio.sleep(1.5)

        # 기존 기록 비교 및 알림 (이전 로직과 동일)
        old_data = []
        is_first_run = not os.path.exists(db_file)
        if not is_first_run:
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 3: continue
                title, _, detail_url = parts
                msg = f"**[{name}] 새로운 소식**\n{detail_url}" if is_first_run else f"**[{name}] 내용 수정 감지!**\n{detail_url}"
                requests.post(WEBHOOK_URL, json={"content": msg})

        # 무조건 저장
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 저장 완료 ({len(current_data)}건)")
            
    except Exception as e:
        print(f"❌ {name} 처리 오류: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        # 세션 분리로 로딩 성능 향상
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
