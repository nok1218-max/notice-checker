import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값 (본인의 정보로 확인)
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"
TARGET_URL = "https://maple.land/board/notices"
DB_FILE = "last_notice.txt"

def check_notice():
    try:
        # 차단 방지를 위한 브라우저 헤더 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        res = requests.get(TARGET_URL, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')

        # 이미지 기반 최신 CSS 선택자 적용
        # 메이플랜드는 현재 flex 구조의 div를 사용 중입니다.
        notice_elements = soup.select('div.flex.flex-col.sm\:flex-row.sm\:items-center')
        
        if not notice_elements:
            # 보조 선택자 (클래스명이 바뀔 경우 대비)
            notice_elements = soup.select('div[class*="transition-colors"]')

        if not notice_elements:
            print("❌ 공지사항 목록을 찾을 수 없습니다. 사이트 구조가 변경되었을 수 있습니다.")
            return

        # 가장 첫 번째(최신) 공지 텍스트 추출 및 정리
        latest_title = notice_elements[0].get_text(separator=' ', strip=True)
        
        # 이전 기록 읽기
        last_title = ""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                last_title = f.read().strip()

        # [비교 로직] 새 공지가 떴을 때만 발송
        if latest_title != last_title:
            print(f"✅ 새 공지 발견: {latest_title}")
            
            # 디스코드 전송 (내용 예쁘게 Embed 형식으로)
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

if __name__ == "__main__":
    check_notice()
