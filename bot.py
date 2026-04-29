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
        # 데이터가 확실히 로드되도록 networkidle 대기
        await page.goto(list_url, wait_until="networkidle", timeout=40000)
        
        # 리스트 박스 대기
        container_selector = "div.w-full.overflow-x-auto.rounded-lg"
        await page.wait_for_selector(container_selector, timeout=20000)
        
        # 실제 게시글 행(div) 추출
        rows = page.locator(f"{container_selector} > div.flex.flex-col")
        count = await rows.count()

        current_data = []
        current_titles = []

        # 상위 10개 추출
        for i in range(min(count, 10)):
            row = rows.nth(i)
            text_content = await row.inner_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            if len(lines) < 2: continue
            
            title_text = lines[1]
            if title_text.endswith(' N'):
                title_text = title_text[:-2].strip()
            
            # 링크 추출
            link_element = row.locator("a").first
            href = await link_element.get_attribute("href")
            detail_url = f"https://maple.land{href}" if href and href.startswith("/") else (href or list_url)

            current_data.append((title_text, detail_url))
            current_titles.append(title_text)

        # 기존 데이터와 비교
        old_titles = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_titles = [line.strip() for line in f if line.strip()]

        # 새 게시글 확인 및 전송
        for title, d_url in reversed(current_data):
            if title not in old_titles:
                if old_titles: # 최초 실행이 아닐 때만 발송
                    msg = f"**[{name}] 새 소식**\n{title}\n{d_url}"
                    
                    # [누락 방지] 디스코드 전송 및 상태 확인
                    res = requests.post(WEBHOOK_URL, json={"content": msg})
                    if res.status_code == 429: # Rate Limit 걸린 경우
                        retry_after = res.json().get('retry_after', 1)
                        await asyncio.sleep(retry_after)
                        requests.post(WEBHOOK_URL, json={"content": msg})
                    
                    print(f"🔔 발송 완료: {title}")
                    # 전송 간격 딜레이 (봇 누락 방지 핵심)
                    await asyncio.sleep(0.8)

        # 파일 업데이트
        if current_titles:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_titles))
            print(f"💾 {name} 완료")

    except Exception as e:
        print(f"❌ {name} 에러: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 실제 사용자처럼 보이도록 User-Agent 설정
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        # [누락 방지] gather 대신 순차적으로 하나씩 처리
        for target in TARGETS:
            await check_board(context, target)
            # 게시판 사이의 짧은 휴식
            await asyncio.sleep(1.5)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
