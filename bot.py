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
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
            rows = page.locator('div.min-w-0.flex-1')
            
            if i >= await rows.count(): break
            
            title_text = (await rows.nth(i).inner_text()).strip()
            if len(title_text) < 2 or title_text in ["공지사항", "이벤트", "개발일지"]: continue
            
            print(f"    └ [{i+1}/5] 클릭: {title_text[:15]}...")
            await rows.nth(i).click()
            
            try:
                # 상세 페이지 로딩 대기
                await page.wait_for_load_state("networkidle", timeout=30000)
                detail_url = page.url
                
                # 1. [핵심] 불필요한 요소(조회수, 시간, 하단 추천글) 제거 후 본문만 추출
                # evaluate를 사용하여 브라우저 내부에서 지저분한 것들을 치우고 텍스트를 가져옵니다.
                clean_content = await page.evaluate("""() => {
                    // 본문 영역 선택 (div.prose가 메이플랜드 본문 핵심)
                    const contentEl = document.querySelector('div.prose');
                    if (!contentEl) return "";

                    // 복사본을 만들어 작업 (원본 훼손 방지)
                    const clone = contentEl.cloneNode(true);
                    
                    // 조회수, 작성일, 댓글수 등 숫자가 자주 바뀌는 요소의 클래스/태그 제거
                    // 보통 공지사항 하단이나 상단에 있는 시간/조회수 관련 요소를 타겟팅합니다.
                    const excludes = clone.querySelectorAll('span, div.text-gray-400, .view-count, .date');
                    excludes.forEach(el => el.remove());

                    return clone.innerText;
                }""")
                
                # 2. 공백 정제 및 글자수 제한
                # 앞뒤 공백을 제거하고, 연속된 공백을 하나로 합칩니다.
                refined_text = " ".join(clean_content.split()).strip()
                
                # 3. 데이터 저장 (비교용 데이터는 앞쪽 500자만 사용 - 하단 잡음 차단)
                if len(refined_text) > 10:
                    # 제목 + 본문앞부분 + URL을 하나의 고유 키로 생성
                    current_data.append(f"{title_text}||{refined_text[:500]}||{detail_url}")
                    print(f"      ✅ 수집 성공 ({len(refined_text)}자)")
                else:
                    print(f"      ⚠️ 본문 내용이 너무 짧아 제외")

            except Exception as e:
                print(f"      ⚠️ 상세 페이지 분석 실패: {type(e).__name__}")
            
            # 목록으로 다시 이동
            await page.goto(list_url, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

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
                
                # 첫 실행 알림 방지 로직 (파일이 없을 땐 기록만 하고 알림은 안 보냄)
                if not is_first_run:
                    msg = f"**[{name}] 내용 수정 또는 새 소식!**\n{d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})

        # 새로운 데이터로 TXT 파일 갱신
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 파일 업데이트 완료")

    except Exception as e:
        print(f"❌ {name} 치명적 오류: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        # 다크 모드 등 스타일 영향을 최소화하기 위해 기본 context 사용
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        for target in TARGETS:
            await check_board(context, target)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
