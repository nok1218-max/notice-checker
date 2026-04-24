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
                # 1. 상세 페이지 로딩 대기 강화
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3) # 넉넉하게 3초 대기 (서버 느림 대비)
                
                detail_url = page.url
                
                # 2. [수정] 본문 추출 로직 유연화
                clean_content = await page.evaluate("""() => {
                    // 순서대로 본문일 가능성이 높은 구역을 탐색
                    const selectors = ['div.prose', 'article', 'main'];
                    let contentEl = null;
                    
                    for (let s of selectors) {
                        let el = document.querySelector(s);
                        // 내용이 너무 짧은 경우(목록 데이터 등) 제외하고 진짜 본문인지 확인
                        if (el && el.innerText.trim().length > 50) {
                            contentEl = el;
                            break;
                        }
                    }

                    if (!contentEl) {
                        // 만약 특정 영역을 못 찾으면, 페이지에서 가장 텍스트가 많은 구역을 강제 선택
                        return document.body.innerText;
                    }

                    const clone = contentEl.cloneNode(true);
                    // 수시로 변하는 숫자/버튼/메타 정보 제거
                    const junk = clone.querySelectorAll('.view-count, .date, span.text-gray-400, button, nav, footer');
                    junk.forEach(j => j.remove());

                    return clone.innerText;
                }""")
                
                refined_text = " ".join(clean_content.split()).strip()
                
                # 3. 데이터 검증 (조회수/카테고리 등이 섞인 목록 데이터인지 확인)
                # 본문 내용이 제목과 완전히 똑같거나 목록 레이아웃이면 제외
                if len(refined_text) > 30 and title_text not in refined_text[:50]:
                    current_data.append(f"{title_text}||{refined_text[:300]}||{detail_url}")
                    print(f"      ✅ 본문 수집 성공")
                else:
                    # 최후의 수단: 본문 클래스를 못 찾아도 일단 저장 (중복 알림 방지용)
                    # 단, 조회수 등이 포함되지 않게 글자만 잘라서 저장
                    current_data.append(f"{title_text}||{refined_text[:200]}||{detail_url}")
                    print(f"      ⚠️ 본문 영역 미탐색 (전체 텍스트 기반 저장)")

            except Exception as e:
                print(f"      ⚠️ 읽기 실패: {type(e).__name__}")
            
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        # 저장 및 알림 (이전과 동일)
        old_data = []
        is_first_run = not os.path.exists(db_file)
        if not is_first_run:
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 3: continue
                title, content, d_url = parts
                if not is_first_run:
                    requests.post(WEBHOOK_URL, json={"content": f"**[{name}] 새 소식/수정**\n{d_url}"})

        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 업데이트 완료")

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
