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

    # 9. 디스코드 발송 (2000자 제한 대응: 초과 시 여러 메시지로 분할)
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        if len(message) <= 2000:
            send_to_discord(message, webhook_url)
        else:
            # 줄 단위로 분할하여 2000자 이내 메시지들로 나눔
            chunks = []
            current_chunk = []
            current_len = 0
            for line in lines:
                line_len = len(line) + 1  # +1 for newline
                if current_len + line_len > 2000 and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_len = line_len
                else:
                    current_chunk.append(line)
                    current_len += line_len
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            for chunk in chunks:
                send_to_discord(chunk, webhook_url)
        print("\n📨 디스코드 발송 완료.")
    else:
        print("\n⚠️ DISCORD_WEBHOOK_URL 환경변수가 없어 디스코드 발송을 건너뜁니다.")


if __name__ == "__main__":
    main()
