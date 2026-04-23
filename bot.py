import os
import asyncio
from playwright.async_api import async_playwright
import requests

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"
TARGET_URL = "https://maple.land/board/notices"
DB_FILE = "last_notice.txt"

async def check_notice():
    async with async_playwright() as p:
        # 브라우저 실행
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 페이지 접속 (네트워크가 조용해질 때까지 대기)
            await page.goto(TARGET_URL, wait_until="networkidle")
            
            # 공지사항 요소가 렌더링될 때까지 대기
            await page.wait_for_selector('div.min-w-0.flex-1')

            # 모든 공지 행(row)을 가져옵니다.
            rows = page.locator('div.min-w-0.flex-1')
            count = await rows.count()
            
            latest_title = ""
            
            for i in range(count):
                text = await rows.nth(i).inner_text()
                text = text.strip()
                
                # "공지사항", "카테고리", "제목" 등 헤더 문구가 포함되면 건너뜁니다.
                if text == "공지사항" or text == "제목" or not text:
                    continue
                
                # 첫 번째로 만나는 유효한 텍스트가 진짜 최신 공지입니다.
                # 줄바꿈이 있으면 한 줄로 합쳐줍니다.
                latest_title = " ".join(text.split())
                break

            if not latest_title:
                print("❌ 공지사항 본문을 찾을 수 없습니다.")
                return

            # 이전 기록 읽기
            last_title = ""
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    last_title = f.read().strip()

            # [비교 로직]
            if latest_title != last_title:
                print(f"✅ 새 공지 발견: {latest_title}")
                
                payload = {
                    "embeds": [{
                        "title": "📢 메이플랜드 새로운 공지사항",
                        "description": latest_title,
                        "url": TARGET_URL,
                        "color": 16753920 # 주황색
                    }]
                }
                requests.post(WEBHOOK_URL, json=payload)
                
                # 새 제목 저장
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    f.write(latest_title)
            else:
                print(f"😴 새로운 공지가 없습니다. (현재 최신: {latest_title})")

        except Exception as e:
            print(f"⚠️ 오류 발생: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_notice())
