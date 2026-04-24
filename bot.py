import os
import asyncio
from playwright.async_api import async_playwright
import requests

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
        
        for i in range(5):
            # 매번 목록을 새로 갱신해서 찾음 (안정성)
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=20000)
            rows = page.locator('div.min-w-0.flex-1')
            
            if i >= await rows.count(): break
            
            title_text = (await rows.nth(i).inner_text()).strip()
            if len(title_text) < 2 or title_text in ["공지사항", "이벤트", "개발일지"]: continue
            
            print(f"    └ [{i+1}/5] 클릭: {title_text[:15]}...")
            
            # 클릭 전 URL 저장
            await rows.nth(i).click()
            
            try:
                # 1. 페이지 로딩 대기 강화
                await page.wait_for_load_state("domcontentloaded")
                detail_url = page.url
                
                # 2. 본문(prose)이 나올 때까지 대기 (더 유연하게 수정)
                # 만약 div.prose가 없으면 article이나 main 내부 텍스트라도 긁어오도록 대기
                await page.wait_for_selector('div.prose, article, main', timeout=20000)
                
                # 본문 추출 시도
                content_loc = page.locator('div.prose')
                if await content_loc.count() > 0:
                    full_content = await content_loc.first.inner_text()
                else:
                    # 대안: 본문 클래스가 없을 경우 상위 컨테이너라도 긁음
                    full_content = await page.locator('main').inner_text()
                
                clean_content = " ".join(full_content.split()).strip()[:1000]
                current_data.append(f"{title_text}||{clean_content}||{detail_url}")
                
            except Exception as e:
                print(f"      ⚠️ 본문 읽기 실패: {type(e).__name__}")
            
            # 목록으로 복귀
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(2) # 서버 부하 방지 및 로딩 대기

        # 저장 및 알림 로직 (동일)
        old_data = []
        is_first_run = not os.path.exists(db_file)
        if not is_first_run:
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 3: continue
                title, _, d_url = parts
                msg = f"**[{name}] 새 소식**\n{d_url}" if is_first_run else f"**[{name}] 수정 감지**\n{d_url}"
                requests.post(WEBHOOK_URL, json={"content": msg})

        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 기록 완료")

    except Exception as e:
        print(f"❌ {name} 탭 치명적 오류: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # 가상 환경에서 더 안정적인 옵션 추가
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
