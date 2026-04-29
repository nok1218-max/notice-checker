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
        print(f"🔍 {name} 스캔 시작...")
        # 렌더링 완료를 위해 networkidle 사용 (데이터 누락 방지)
        await page.goto(list_url, wait_until="networkidle", timeout=30000)
        
        # 게시글 요소들이 로드될 때까지 대기
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=15000)
        
        # 상세 페이지 클릭 대신, 링크를 포함한 부모 요소를 찾습니다.
        # 메플랜드 구조상 div 상위의 a 태그를 찾는 것이 안전합니다.
        items = page.locator('a[href*="/board/"]') 
        count = await items.count()

        current_data = [] # (제목, URL) 튜플 저장
        
        for i in range(min(count, 10)): # 넉넉하게 상위 10개 검사
            item = items.nth(i)
            href = await item.get_attribute("href")
            if not href: continue
            
            # 절대 경로 생성
            detail_url = f"https://maple.land{href}" if href.startswith("/") else href
            
            # 텍스트 추출 및 정제
            raw_text = await item.inner_text()
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            # 보통 첫 번째 줄이 제목입니다. 'N' 표시 제거 로직 포함
            if not lines: continue
            title = lines[0]
            if title.endswith(' N'): title = title[:-2].strip()
            
            # 중복/필터링
            if title in ["공지사항", "이벤트", "개발일지"] or len(title) < 2:
                continue
                
            current_data.append((title, detail_url))

        # 기존 데이터 불러오기
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        # 새 게시글 확인 (역순으로 알림 보내기)
        new_items = []
        for title, d_url in current_data:
            if title not in old_titles:
                new_items.append((title, d_url))
        
        # 새 글이 있으면 알림 전송
        for title, d_url in reversed(new_items):
            msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
            requests.post(WEBHOOK_URL, json={"content": msg})
            print(f"🔔 새 알림: {title}")

        # 파일 갱신 (최신 데이터 저장)
        if current_data:
            with open(db_file, "w", encoding="utf-8") as f:
                # 제목만 저장
                f.write("\n".join([item[0] for item in current_data]))
            print(f"💾 {name} 업데이트 완료 ({len(new_items)}개 신규)")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 시 user_agent를 설정하면 차단 확률이 줄어듭니다.
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        tasks = [check_board(context, target) for target in TARGETS]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
