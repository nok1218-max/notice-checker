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
        print(f"🔍 {name} 스캔 시작...")
        # 페이지 로딩 대기
        await page.goto(list_url, wait_until="networkidle", timeout=30000)
        
        # [핵심] 스크린샷에서 확인된 리스트 컨테이너가 나타날 때까지 대기
        container_selector = "div.w-full.overflow-x-auto.rounded-lg"
        await page.wait_for_selector(container_selector, timeout=15000)
        
        # 컨테이너 바로 아래에 있는 게시글 아이템(div)들만 선택
        # 메뉴 텍스트가 섞이는 것을 방지하기 위해 자식 결합자(>) 사용
        rows = page.locator(f"{container_selector} > div.flex.flex-col")
        count = await rows.count()

        current_data = [] # (제목, URL) 저장
        current_titles = []

        for i in range(min(count, 10)): # 최신순으로 최대 10개 검사
            row = rows.nth(i)
            
            # 1. 텍스트 추출 및 정제
            text_content = await row.inner_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            # 스크린샷 구조상: lines[0]=카테고리, lines[1]=제목, lines[2]=날짜
            if len(lines) < 2:
                continue
                
            title_text = lines[1]
            # 'N' (New 아이콘) 제거
            if title_text.endswith(' N'):
                title_text = title_text[:-2].strip()
            
            # 2. URL 추출 (상세 페이지 클릭 대신 href 속성 찾기)
            # 보통 row(div) 내부에 a 태그가 있거나, row 자체가 a 태그일 수 있음
            link_element = row.locator("a").first
            href = await link_element.get_attribute("href")
            
            if not href:
                # 만약 a 태그를 못 찾으면 안전하게 클릭 방식으로 URL 획득 (예외 케이스)
                await row.click()
                await page.wait_for_load_state("commit")
                detail_url = page.url
                await page.go_back(wait_until="domcontentloaded")
            else:
                detail_url = f"https://maple.land{href}" if href.startswith("/") else href

            current_data.append((title_text, detail_url))
            current_titles.append(title_text)

        # 3. 데이터 비교 및 알림
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        # 새 게시글 확인 (역순으로 알림 보내기)
        new_found = False
        for title, d_url in reversed(current_data):
            if title not in old_titles:
                # 최초 실행 시(파일이 없을 때) 알림 폭탄 방지
                if old_titles:
                    msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                    requests.post(WEBHOOK_URL, json={"content": msg})
                    print(f"🔔 새 게시글 발송: {title}")
                new_found = True

        # 4. 파일 업데이트
        if current_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_titles))
            print(f"💾 {name} 완료 (상태 유지)")

    except Exception as e:
        print(f"❌ {name} 에러 발생: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # 실제 브라우저와 유사한 환경 설정 (User-Agent 등)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # 모든 게시판 동시 스캔
        tasks = [check_board(context, target) for target in TARGETS]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
