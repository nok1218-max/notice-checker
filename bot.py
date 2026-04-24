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
        # 60초까지 넉넉하게 대기
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        
        current_data = []
        
        for i in range(5):
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
            rows = page.locator('div.min-w-0.flex-1')
            
            if i >= await rows.count(): break
            
            title_text = (await rows.nth(i).inner_text()).strip()
            # 메뉴나 잡음 텍스트 필터링
            if len(title_text) < 2 or title_text in ["공지사항", "이벤트", "개발일지"]: continue
            
            print(f"    └ [{i+1}/5] 클릭: {title_text[:15]}...")
            await rows.nth(i).click()
            
            try:
                # 1. 상세 페이지 로딩 대기 강화 (네트워크 활동이 멈출 때까지)
                await page.wait_for_load_state("networkidle", timeout=30000)
                detail_url = page.url
                
                # 2. 본문 영역이 나타날 때까지 대기
                # Mapleland의 본문 구조는 div.prose가 주를 이루지만, 대안 선택자도 추가
                await page.wait_for_selector('div.prose, article, main', timeout=30000)
                
                # 3. [핵심] 특정 태그에 의존하지 않고 화면상의 텍스트를 긁어오기
                # evaluate를 사용하면 브라우저 내부에서 렌더링된 텍스트를 직접 가져옵니다.
                full_content = await page.evaluate("""() => {
                    const el = document.querySelector('div.prose') || document.querySelector('article') || document.querySelector('main');
                    return el ? el.innerText : document.body.innerText;
                }""")
                
                clean_content = " ".join(full_content.split()).strip()
                
                # 본문이 너무 짧으면 로딩 실패로 간주하고 저장 안 함 (중복 전송 방지)
                if len(clean_content) > 10:
                    current_data.append(f"{title_text}||{clean_content[:1000]}||{detail_url}")
                    print(f"      ✅ 수집 성공 ({len(clean_content)}자)")
                else:
                    print(f"      ⚠️ 본문 내용 부족으로 제외")
                
            except Exception as e:
                print(f"      ⚠️ 본문 읽기 실패: {type(e).__name__}")
            
            # 목록으로 다시 이동 (안정성을 위해 goto 사용)
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        # 비교 및 저장 로직
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
                msg = f"**[{name}] 새 소식**\n{d_url}" if is_first_run else f"**[{name}] 내용 수정 감지!**\n{d_url}"
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
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
