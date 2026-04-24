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
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()
        
        current_data = [] 
        check_limit = min(count, 5) # 상위 5개 추출
        
        for i in range(check_limit):
            title_text = await rows.nth(i).inner_text()
            title_text = " ".join(title_text.split()).strip()
            
            # 무의미한 텍스트 필터링
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue
            
            # 게시글 클릭하여 본문 진입
            await rows.nth(i).click()
            try:
                detail_url = page.url 
                await page.wait_for_selector('div.prose', timeout=20000)
                full_content = await page.inner_text('div.prose')
                # 본문 텍스트 정리 (감지용)
                clean_content = " ".join(full_content.split()).strip()[:1000]
                current_data.append(f"{title_text}||{clean_content}||{detail_url}")
            except:
                print(f"      ⚠️ {title_text[:10]} 본문 읽기 실패")
            
            await page.go_back()
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=20000)
            await asyncio.sleep(1)

        # 기존 DB 로드
        old_data = []
        is_first_run = not os.path.exists(db_file)
        if not is_first_run:
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        # 비교 및 알림 전송
        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 3: continue
                title, _, detail_url = parts
                
                # 첫 실행이면 새 글 알림, 이후엔 수정 알림
                if is_first_run:
                    msg = f"**[{name}] 새로운 소식**\n{detail_url}"
                else:
                    msg = f"**[{name}] 내용 수정 감지!**\n{detail_url}"
                
                requests.post(WEBHOOK_URL, json={"content": msg})
                print(f"      ✅ 전송: {title[:15]}")

        # 현재 상태를 TXT로 무조건 업데이트 (기록용)
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            
    except Exception as e:
        print(f"❌ {name} 처리 오류: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()
        print("🏁 전수 조사 완료.")

if __name__ == "__main__":
    asyncio.run(main())
