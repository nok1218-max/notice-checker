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
        
        # 목록 요소가 뜰 때까지 대기
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        rows_locator = page.locator('div.min-w-0.flex-1')
        count = await rows_locator.count()

        processed_count = 0
        for i in range(count):
            if processed_count >= 5: break # 상위 5개만

            row = rows_locator.nth(i)
            title_text = (await row.inner_text()).strip()
            
            # [필터링] 무의미한 텍스트 및 메뉴 제목 건너뛰기
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue

            print(f"    └ [{processed_count+1}/5] 클릭: {title_text[:15]}...")
            await row.click()
            processed_count += 1
            
            try:
                # 1. 상세 페이지 로딩 대기 (DOM이 완성될 때까지)
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2) # 렌더링 시간 추가 확보
                detail_url = page.url
                
                # 2. 본문 추출 (더 넓은 선택자 사용: prose 또는 article 또는 main)
                # 메이플랜드 상세 페이지의 글 내용 영역을 강제로 긁음
                full_content = await page.evaluate("""() => {
                    const selectors = ['div.prose', 'article', 'main', '.min-h-screen'];
                    for (let s of selectors) {
                        const el = document.querySelector(s);
                        if (el && el.innerText.length > 50) {
                            // 조회수, 날짜 등 숫자 포함 요소 제거 시도
                            const junk = el.querySelectorAll('.view-count, .date, span.text-gray-400');
                            junk.forEach(j => j.remove());
                            return el.innerText;
                        }
                    }
                    return document.body.innerText; // 최후의 수단
                }""")
                
                refined_text = " ".join(full_content.split()).strip()
                
                # 본문이 어느 정도 로딩되었을 때만 저장
                if len(refined_text) > 20:
                    current_data.append(f"{title_text}||{refined_text[:500]}||{detail_url}")
                    print(f"      ✅ 수집 성공 ({len(refined_text)}자)")
                else:
                    print(f"      ⚠️ 본문 로딩 미흡 (스킵)")

            except Exception as e:
                print(f"      ⚠️ 읽기 오류: {type(e).__name__}")
            
            # 다시 목록으로 (안정성을 위해 주소 직접 이동)
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        # 비교/알림/저장 로직
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
                if not is_first_run:
                    requests.post(WEBHOOK_URL, json={"content": f"**[{name}] 새 소식/수정**\n{d_url}"})

        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 저장 완료")

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
