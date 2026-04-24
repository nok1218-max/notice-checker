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
    db_file = f"last_{name}.txt"
    
    page = await context.new_page()
    try:
        print(f"🔍 {name} 목록 확인 중...")
        # 네트워크 유휴 상태까지 대기하여 게시글 목록이 확실히 뜨도록 함
        await page.goto(list_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('div.min-w-0.flex-1', timeout=30000)
        
        rows = page.locator('div.min-w-0.flex-1')
        count = await rows.count()
        
        current_data = [] # "제목||본문내용||상세URL" 형태로 저장
        
        # 최신 5개 항목에 대해 상세 페이지 전수 조사
        check_limit = min(count, 5)
        for i in range(check_limit):
            # 목록에서 제목 추출
            title_text = await rows.nth(i).inner_text()
            title_text = " ".join(title_text.split()).strip()
            
            # 필터링: 불필요한 키워드 제외
            if title_text in ["공지사항", "이벤트", "개발일지", "카테고리", "제목", ""] or len(title_text) < 3:
                continue
            
            print(f"   └ [{i+1}/{check_limit}] 상세 분석: {title_text[:20]}...")

            # 해당 게시글 클릭하여 입장
            await rows.nth(i).click()
            
            try:
                # 1. 상세 페이지의 실제 고유 URL 수집
                detail_url = page.url 
                
                # 2. 본문 내용 로딩 대기 및 추출 (메이플랜드 본문 영역 선택자: div.prose)
                await page.wait_for_selector('div.prose', timeout=20000)
                full_content = await page.inner_text('div.prose')
                
                # 3. 텍스트 정리 (줄바꿈, 공백 제거 후 앞부분 1000자 수집)
                clean_content = " ".join(full_content.split()).strip()[:1000]
                
                # 데이터 세트 구성 (중복 알림 방지용 비교 데이터)
                current_data.append(f"{title_text}||{clean_content}||{detail_url}")
                
            except Exception as e:
                print(f"   ⚠️ 상세 페이지 본문 수집 실패: {e}")
            
            # 4. 다시 목록으로 돌아가서 다음 글 준비
            await page.go_back()
            await page.wait_for_selector('div.min-w-0.flex-1', timeout=20000)
            await asyncio.sleep(1.5) # 사이트 부하 방지를 위한 짧은 휴식

        # --- 데이터 비교 및 알림 발송 ---
        old_data = []
        if os.path.exists(db_file):
            with open(db_file, "r", encoding="utf-8") as f:
                old_data = [line.strip() for line in f.readlines() if line.strip()]

        new_found = False
        # 리스트를 뒤집어서 오래된 글부터 순차적으로 알림 발송
        for item in reversed(current_data):
            if item not in old_data:
                parts = item.split("||")
                if len(parts) < 3: continue
                
                title, content, detail_url = parts
                
                # 요청하신 제목 형식: 제목 - 공지사항 | Mapleland
                display_title = f"{title} - {name} | Mapleland"
                
                # 카테고리별 디스코드 임베드 색상 설정
                color = 16753920 if name == "공지사항" else (3447003 if name == "이벤트" else 10181046)
                
                payload = {
                    "embeds": [{
                        "title": display_title,
                        "description": f"{content[:400]}...", # 본문 앞부분 400자 미리보기
                        "url": detail_url, # 클릭 시 게시글로 바로 이동
                        "color": color,
                        "footer": {"text": "새로운 업데이트나 본문 수정이 감지되었습니다."}
                    }]
                }
                
                response = requests.post(WEBHOOK_URL, json=payload)
                if response.status_code == 204:
                    print(f"✅ 디스코드 알림 전송 성공: {title}")
                new_found = True

        # --- 데이터베이스(텍스트 파일) 업데이트 ---
        if new_found:
            with open(db_file, "w", encoding="utf-8") as f:
                f.write("\n".join(current_data))
            print(f"💾 {name} 최신 데이터 저장 완료.")
        else:
            print(f"😴 {name} 변동 사항 없음.")

    except Exception as e:
        print(f"⚠️ {name} 처리 중 전체 오류 발생: {e}")
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (headless=True는 창을 띄우지 않음)
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        
        # 실제 사용자처럼 보이도록 User-Agent 설정
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        for target in TARGETS:
            await check_board(context, target)
            await asyncio.sleep(3) # 타겟 게시판 사이 대기 시간
            
        await browser.close()
        print("🏁 모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    asyncio.run(main())
