# Discord Notification via GitHub Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매일 장 마감 후 거래대금 500억 이상 상승률 Top 10 종목을 디스코드로 자동 발송한다.

**Architecture:** Python 스크립트(`top_movers.py`)에서 pykrx 데이터 조회와 Discord Webhook 발송을 모두 처리한다. GitHub Actions cron으로 월~금 KST 18:00에 실행하며, 휴장일이면 조기 종료한다.

**Tech Stack:** Python 3.12, pykrx, requests, GitHub Actions

---

### Task 1: requirements.txt 생성

**Files:**
- Create: `requirements.txt`

**Step 1: requirements.txt 작성**

```
pykrx
requests
```

**Step 2: 커밋**

```bash
git add requirements.txt
git commit -m "feat: add requirements.txt with pykrx and requests"
```

---

### Task 2: top_movers.py 수정 - 날짜 자동 계산 및 휴장일 판단

**Files:**
- Modify: `top_movers.py`

**Step 1: 스크립트 수정**

`top_movers.py`를 다음과 같이 수정한다:

- `target_date`를 하드코딩 대신 `datetime.today().strftime("%Y%m%d")`로 변경
- pykrx 조회 후 DataFrame이 비어있으면 "휴장일" 메시지를 출력하고 `sys.exit(0)`
- 디스코드 발송 함수 `send_to_discord(message, webhook_url)` 추가
- 환경변수 `DISCORD_WEBHOOK_URL`이 있으면 디스코드 발송, 없으면 콘솔 출력만 수행
- 메시지를 문자열로 조립하여 콘솔 출력 + 디스코드 발송에 공용으로 사용

```python
import os
import sys
from datetime import datetime

import requests
from pykrx import stock


def send_to_discord(message: str, webhook_url: str) -> None:
    """디스코드 Webhook으로 메시지를 발송한다."""
    payload = {"content": message}
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()


def main():
    # 1. 날짜 설정
    target_date = datetime.today().strftime("%Y%m%d")
    min_trading_value = 50_000_000_000  # 500억 원

    # 2. 전 종목 시세 데이터 가져오기
    df = stock.get_market_price_change(target_date, target_date)

    # 3. 휴장일 판단
    if df.empty:
        print(f"{target_date}은(는) 휴장일입니다. 스킵합니다.")
        sys.exit(0)

    # 4. 주식 종목만 필터링 (ETF/ETN 제외)
    stock_tickers = stock.get_market_ticker_list(market="ALL")
    df_stocks = df.loc[df.index.isin(stock_tickers)]

    # 5. 거래대금 조건 필터링 (500억 이상)
    df_filtered = df_stocks[df_stocks["거래대금"] >= min_trading_value].copy()

    if df_filtered.empty:
        print(f"{target_date}: 거래대금 500억 이상 종목이 없습니다.")
        sys.exit(0)

    # 6. 상승률 기준 정렬 및 상위 10개 추출
    rising_heavy = df_filtered.sort_values(by="등락률", ascending=False).head(10)
    rising_heavy["거래대금(억)"] = (rising_heavy["거래대금"] / 100_000_000).round(1)

    # 7. 메시지 조립
    date_display = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
    lines = []
    lines.append(f"🏆 {date_display} '돈 몰린' 급등주 Top 10 (거래대금 500억 이상)")
    lines.append("━" * 50)
    lines.append(f"{'종목명':<10} | {'종가':>10} | {'상승률':>8} | {'거래대금(억원)':>12}")
    lines.append("━" * 50)

    for _, row in rising_heavy.iterrows():
        lines.append(
            f"{row['종목명']:<10} | {row['종가']:>10,}원 | "
            f"{row['등락률']:>+7.2f}% | {row['거래대금(억)']:>10,.1f}억"
        )

    lines.append("━" * 50)
    lines.append(
        f"✅ 총 {len(df_filtered)}개 종목이 거래대금 500억 원을 넘겼습니다."
    )

    message = "\n".join(lines)

    # 8. 출력
    print(message)

    # 9. 디스코드 발송
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        send_to_discord(message, webhook_url)
        print("\n📨 디스코드 발송 완료.")
    else:
        print("\n⚠️ DISCORD_WEBHOOK_URL 환경변수가 없어 디스코드 발송을 건너뜁니다.")


if __name__ == "__main__":
    main()
```

**Step 2: 로컬 테스트 (콘솔 출력만 확인)**

```bash
python top_movers.py
```

Expected: 콘솔에 결과 출력, "DISCORD_WEBHOOK_URL 환경변수가 없어..." 메시지 표시

**Step 3: 커밋**

```bash
git add top_movers.py
git commit -m "feat: auto-date, holiday detection, discord webhook support"
```

---

### Task 3: GitHub Actions 워크플로우 생성

**Files:**
- Create: `.github/workflows/top-movers.yml`

**Step 1: 워크플로우 파일 작성**

```yaml
name: Top Movers Discord Notification

on:
  schedule:
    # UTC 09:00 = KST 18:00, 월~금
    - cron: '0 9 * * 1-5'
  workflow_dispatch:

jobs:
  notify:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run top movers script
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: python top_movers.py
```

**Step 2: 커밋**

```bash
git add .github/workflows/top-movers.yml
git commit -m "feat: add GitHub Actions workflow for daily discord notification"
```

---

### Task 4: Git 저장소 초기화 및 최종 확인

**Step 1: git 저장소 초기화 (아직 아닌 경우)**

```bash
git init
```

**Step 2: 전체 파일 확인**

```bash
git status
```

Expected: `top_movers.py`, `requirements.txt`, `.github/workflows/top-movers.yml`, `docs/plans/` 확인

**Step 3: 최종 커밋 (필요시)**

---

## Setup Guide (사용자 수동 작업)

GitHub 리포지토리에서 다음을 설정해야 한다:

1. **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DISCORD_WEBHOOK_URL`
3. Value: 디스코드 채널의 Webhook URL
   - 디스코드 채널 설정 → 연동 → 웹후크 → 새 웹후크 → URL 복사
