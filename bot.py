import os
import asyncio
from playwright.async_api import async_playwright
import requests

# 1. 설정값 (디스코드 웹훅 주소)
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
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
            rows = page.locator('div.min-w-0.flex-1')
            
            if i >= await rows.count(): break
            
            title_text = (await rows.nth(i).inner_text()).strip()
            # 메뉴명이나 짧은 텍스트 필터링
            if len(title_text) < 2 or title_text in ["공지사항", "이벤트", "개발일지"]: continue
            
            print(f"    └ [{i+1}/5] 클릭: {title_text[:15]}...")
            await rows.nth(i).click()
            
            try:
                # 상세 페이지 로딩 대기
                await page.wait_for_load_state("networkidle", timeout=30000)
                detail_url = page.url
                
                # 2. [핵심] 조회수, 날짜 등 잡음 제거 로직 (JS 실행)
                clean_content = await page.evaluate("""() => {
                    const contentEl = document.querySelector('div.prose') || document.querySelector('article');
                    if (!contentEl) return "";

                    const clone = contentEl.cloneNode(true);
                    
                    // 조회수, 작성일, 댓글수, 하단 메뉴 등 수시로 변하는 요소의 클래스/태그 제거
                    const selectorsToRemove = [
                        '.view-count', '.date', '.comment-count', 
                        'span.text-gray-400', 'div.flex.items-center.gap-2',
                        'header', 'footer', 'button', 'nav'
                    ];
                    
                    selectorsToRemove.forEach(s => {
                        const elements = clone.querySelectorAll(s);
                        elements.forEach(el => el.remove());
                    });

                    return clone.innerText;
                }""")
                
                # 3. 텍스트 정제 (연속 공백 제거 및 제목 결합)
                refined_text = " ".join(clean_content.split()).strip()
                
                # 본문이 정상적으로 읽혔을 때만 저장 (앞 500자만 비교하여 변동 최소화)
                if len(refined_text) > 10:
                    current_data.append(f"{title_text}||{refined_text[:500]}||{detail_url}")
                    print(f"      ✅ 수집 완료")
                else:
                    print(f"      ⚠️ 본문 로딩 실패로 스킵")

            except Exception as e:
                print(f"      ⚠️ 본문 읽기 실패: {type(e).__name__}")
            
            # 목록으로 다시 이동
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

        # 기존 데이터와 비교
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
                
                # 첫 실행 시에는 기록만 하고 알림은 안 보냄 (중복 방지)
                if not is_first_run:
                    msg = f"**[{name}] 내용 수정 또는 새 소식!**\n{d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})

        # 파일 갱신
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
