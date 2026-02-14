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
    # 1. 날짜 설정 (TARGET_DATE 환경변수가 있으면 사용, 없으면 오늘)
    target_date = os.environ.get("TARGET_DATE") or datetime.today().strftime("%Y%m%d")
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
    table_lines = []
    table_lines.append(f"{'종목명':<10} {'종가':>10} {'상승률':>8} {'거래대금(억)':>10}")
    table_lines.append("-" * 45)

    for _, row in rising_heavy.iterrows():
        table_lines.append(
            f"{row['종목명']:<10} {row['종가']:>10,}원 {row['등락률']:>+7.2f}% {row['거래대금(억)']:>10,.1f}억"
        )

    message = f"기준일: {date_display}\n```\n" + "\n".join(table_lines) + "\n```"

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
