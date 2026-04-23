import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"
TARGET_URL = "https://maple.land/board/notices"
DB_FILE = "last_notice.txt"

def check_notice():
    try:
        # 브라우저처럼 보이게 헤더 강화
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get(TARGET_URL, headers=headers, timeout=10) # 타임아웃 추가
        res.raise_for_status() # 접속 에러 시 바로 예외처리
        
        soup = BeautifulSoup(res.text, 'html.parser')

        # 데이터가 있는지 확인 후 추출
        notice_list = soup.select('.board-notice-list .title-cell')
        
        if not notice_list:
            print("공지 목록을 찾을 수 없습니다. CSS 선택자를 확인하세요.")
            return

        latest_title = notice_list[0].text.strip()

        # 이전 공지와 비교
        last_title = ""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                last_title = f.read().strip()

        if latest_title != last_title:
            # 새 공지가 있으면 디스코드 발송
            msg = {"content": f"📢 **새 공지 등록!**\n{latest_title}"}
            requests.post(WEBHOOK_URL, json=msg)
            
            # 새 공지 제목 저장
            with open(DB_FILE, "w", encoding="utf-8") as f:
                f.write(latest_title)
            print(f"새 공지 발송 완료: {latest_title}")
        else:
            print("새로운 공지가 없습니다.")

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_notice()
