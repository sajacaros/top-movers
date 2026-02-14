# Discord Notification via GitHub Actions - Design

## Overview

거래대금 500억 이상 상승률 Top 10 종목을 매일 장 마감 후 디스코드로 자동 발송한다.

## Architecture

- **방식**: Python 스크립트에서 데이터 조회 + 디스코드 Webhook 발송을 모두 처리
- **스케줄**: GitHub Actions cron (UTC 09:00 = KST 18:00, 월~금)
- **거래일 판단**: pykrx 조회 결과가 비어있으면 휴장일로 판단, 스킵

## Project Structure

```
top-movers/
├── top_movers.py          # 메인 스크립트 (데이터 조회 + 디스코드 발송)
├── requirements.txt       # 의존성 (pykrx, requests)
└── .github/
    └── workflows/
        └── top-movers.yml # GitHub Actions 워크플로우
```

## Changes to top_movers.py

1. `target_date`를 오늘 날짜 자동 계산으로 변경
2. 휴장일 판단 로직 추가 (빈 DataFrame → 조기 종료)
3. 디스코드 Webhook 발송 함수 추가 (`requests` 사용)
4. Webhook URL은 환경변수 `DISCORD_WEBHOOK_URL`에서 읽음
5. 메시지 포맷: 텍스트 기반 (현재 콘솔 출력과 유사)

## Discord Message Format

```
🏆 2026-02-13 '돈 몰린' 급등주 Top 10 (거래대금 500억 이상)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
종목명         | 종가        | 상승률   | 거래대금(억원)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
삼성전자       |   72,000원 |  +3.50% |      1,234.5억
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 총 25개 종목이 거래대금 500억 원을 넘겼습니다.
```

## GitHub Actions Workflow

- **Trigger**: `cron: '0 9 * * 1-5'` (UTC 09:00 = KST 18:00), `workflow_dispatch`
- **Steps**: Python 설치 → 의존성 설치 → 스크립트 실행
- **Secrets**: `DISCORD_WEBHOOK_URL`

## Dependencies

- `pykrx`: 한국 주식 시세 데이터
- `requests`: 디스코드 Webhook HTTP 요청
