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
        rows_locator = page.locator('div.min-w-0.flex-1')
        
        processed_count = 0
        for i in range(await rows_locator.count()):
            if processed_count >= 5: break

            row = rows_locator.nth(i)
            title_text = (await row.inner_text()).strip()
            
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 2:
                continue

            print(f"    └ [{processed_count+1}/5] 클릭: {title_text[:15]}...")
            await row.click()
            processed_count += 1
            
            try:
                # 상세 페이지 로딩 충분히 대기
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2) 
                
                detail_url = page.url
                
                # [핵심] 본문 영역(prose)만 정밀 추출 + 조회수/날짜 태그 제거
                clean_content = await page.evaluate("""() => {
                    const el = document.querySelector('div.prose');
                    if (!el) return "";

                    const clone = el.cloneNode(true);
                    
                    // 조회수, 날짜, 댓글수 등 숫자가 포함된 메타 정보 태그들 삭제
                    const junk = clone.querySelectorAll('.view-count, .date, span.text-gray-400, .flex.gap-2, button');
                    junk.forEach(j => j.remove());

                    return clone.innerText;
                }""")
                
                refined_text = " ".join(clean_content.split()).strip()
                
                # 목록 데이터가 섞여 들어왔는지 검증 (조회수, 카테고리 단어가 포함되면 잘못 긁은 것)
                if len(refined_text) > 20 and not ("조회수" in refined_text and "카테고리" in refined_text):
                    # 앞부분 300자만 비교하여 하단 잡음 차단
                    current_data.append(f"{title_text}||{refined_text[:300]}||{detail_url}")
                    print(f"      ✅ 본문 정제 완료")
                else:
                    print(f"      ⚠️ 본문 수집 실패 또는 데이터 혼입 (스킵)")

            except Exception as e:
                print(f"      ⚠️ 읽기 오류: {type(e).__name__}")
            
            # 목록으로 복귀
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(1)

        # 비교 및 저장
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
                
                # 첫 실행 알림 방지 로직
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
