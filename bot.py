import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값 (본인의 웹훅 주소와 타겟 사이트 주소 입력)
WEBHOOK_URL = "https://discord.com/api/webhooks/1496774829611679744/_keUpah8H1wPyBqMbhosb_71dr4amHQvyguQC6wpqpzNeb1rVj8I0uayV53RwTsEMvej"
TARGET_URL = "https://maple.land/board/notices"
DB_FILE = "last_notice.txt"

def check_notice():
    try:
        # 사이트 데이터 가져오기
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(TARGET_URL, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        # [수정 필요] 사이트의 공지사항 제목 태그를 정확히 찾아야 합니다.
        # 예: soup.select_one('.notice_title').text
        latest_title = soup.select('.board-notice-list .title-cell')[0].text.strip()

        # 이전 공지와 비교
        last_title = ""
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                last_title = f.read().strip()

        if latest_title != last_title:
            # 새 공지가 있으면 디스코드 발송
            requests.post(WEBHOOK_URL, json={"content": f"📢 **새 공지 등록!**\n{latest_title}"})
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
