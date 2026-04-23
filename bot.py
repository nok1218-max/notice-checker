import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"
TARGET_URL = "https://maple.land/board/notices"
DB_FILE = "last_notice.txt"  # 마지막 공지를 기록할 파일

def check_notice():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get(TARGET_URL, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        notice_list = soup.select('.board-notice-list .title-cell')
        
        if not notice_list:
            print("공지 목록을 찾을 수 없습니다.")
            return

        # 현재 사이트의 가장 최신 공지 제목
        current_latest = notice_list[0].text.strip()

        # 기존에 저장된 공지 제목 읽기
        last_recorded = ""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                last_recorded = f.read().strip()

        # [핵심 로직] 새로운 공지일 때만 실행
        if current_latest != last_recorded:
            print(f"새 공지 발견! 발송 중: {current_latest}")
            
            # 디스코드 알림 메시지 구성
            msg = {
                "embeds": [{
                    "title": "📢 메이플랜드 새 공지사항",
                    "description": current_latest,
                    "url": TARGET_URL,
                    "color": 16753920  # 주황색 포인트
                }]
            }
            requests.post(WEBHOOK_URL, json=msg)
            
            # 새로운 공지 제목을 파일에 기록 (다음 비교를 위해)
            with open(DB_FILE, "w", encoding="utf-8") as f:
                f.write(current_latest)
        else:
            print(f"새로운 공지가 없습니다. (현재 최신: {current_latest})")

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_notice()
