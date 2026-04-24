import os
import asyncio
import re
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
        # 목록 로딩 대기
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        rows_locator = page.locator('div.min-w-0.flex-1')
        
        processed_count = 0
        for i in range(await rows_locator.count()):
            if processed_count >= 5: break

            row = rows_locator.nth(i)
            title_text = (await row.inner_text()).strip()
            
            # 필터링: 메뉴나 무의미한 텍스트 제외
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue

            print(f"    └ [{processed_count+1}/5] 클릭: {title_text[:15]}...")
            await row.click()
            processed_count += 1
            
            try:
                # 상세 페이지 로딩 대기 강화
                await page.wait_for_load_state("networkidle", timeout=30000)
                # 본문(prose)이 보일 때까지 끈질기게 대기 (최대 15초)
                try:
                    await page.wait_for_selector('div.prose', state="visible", timeout=15000)
                except:
                    pass 

                detail_url = page.url
                
                # [핵심] 본문 추출
                raw_content = await page.evaluate("""() => {
                    const el = document.querySelector('div.prose') || document.querySelector('article');
                    return el ? el.innerText : "";
                }""")
                
                if not raw_content:
                    print("      ⚠️ 본문을 찾지 못함 (스킵)")
                    continue

                # [필터] 숫자, 공백, 특수문자를 모두 제거 (순수 텍스트만 남김)
                # 조회수 '43,202'와 '43,205'를 동일하게 취급하기 위함
                clean_text = re.sub(r'[^가-힣a-zA-Z]', '', raw_content)
                
                if len(clean_text) > 20:
                    # 비교용 데이터 저장 (제목 + 숫자 뺀 본문 300자)
                    current_data.append(f"{title_text}||{clean_text[:300]}||{detail_url}")
                    print(f"      ✅ 정밀 수집 완료 (숫자 무시 적용)")
                else:
                    print(f"      ⚠️ 유효 내용 부족")

            except Exception as e:
                print(f"      ⚠️ 읽기 오류: {type(e).__name__}")
            
            # 다시 목록으로
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        # 비교 및 알림 로직
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
                
                # 첫 실행 시에는 기록만 하고 알림은 안 보냄
                if not is_first_run:
                    requests.post(WEBHOOK_URL, json={"content": f"**[{name}] 새 소식/수정**\n{d_url}"})

        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 업데이트 성공")

    except Exception as e:
        print(f"❌ {name} 치명적 오류: {e}")
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
