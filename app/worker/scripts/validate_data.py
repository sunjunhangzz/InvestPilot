"""Data quality validation script.

Validates all data tables against sanity checks, coverage thresholds,
and cross-source consistency rules.  Prints a report and logs
failures to data/logs/validation.log.

Usage:
    python app/worker/scripts/validate_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.worker.src.db import database_connection
from app.worker.src.loggers import write_json_log


def main() -> int:
    failures = 0

    with database_connection() as c:
        c.row_factory = None

        # ============================================
        # 1. stocks 股票列表
        # ============================================
        print("=== stocks ===")
        total = c.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
        main_board = c.execute("SELECT COUNT(*) FROM stocks WHERE board='主板' AND is_active=1").fetchone()[0]
        st = c.execute("SELECT COUNT(*) FROM stocks WHERE is_st=1").fetchone()[0]
        dupes = c.execute("SELECT code, COUNT(*) FROM stocks GROUP BY code HAVING COUNT(*)>1").fetchall()

        ok = 5000 <= total <= 6000
        print(f"  总数={total} {'✅' if ok else '❌ (<5000 or >6000)'}")
        if not ok: failures += 1

        ok = 2800 <= main_board <= 3500
        print(f"  主板活跃={main_board} {'✅' if ok else '❌ (<2800 or >3500)'}")
        if not ok: failures += 1

        print(f"  ST={st} (≥0 ✅)")
        print(f"  重复代码={len(dupes)} {'✅' if len(dupes)==0 else '❌'}")

        # 行业覆盖率
        ind_cov = c.execute("SELECT COUNT(*) FROM stocks WHERE industry IS NOT NULL").fetchone()[0]
        ind_pct = round(ind_cov / total * 100, 1) if total > 0 else 0
        ok = ind_pct >= 90
        print(f"  行业覆盖率={ind_pct}% {'✅' if ok else '❌ (<90%)'}")
        if not ok: failures += 1

        # ============================================
        # 2. daily_prices 行情
        # ============================================
        print("\n=== daily_prices ===")
        codes_with_prices = c.execute("SELECT COUNT(DISTINCT code) FROM daily_prices").fetchone()[0]
        pct = round(codes_with_prices / main_board * 100, 1) if main_board > 0 else 0
        ok = pct >= 50
        print(f"  覆盖={codes_with_prices}/{main_board} ({pct}%) {'✅' if ok else '❌ (<50%)'}")
        if not ok: failures += 1

        # Sanity: negative close
        neg_close = c.execute("SELECT COUNT(*) FROM daily_prices WHERE close <= 0").fetchone()[0]
        print(f"  close≤0={neg_close} {'✅' if neg_close==0 else '❌'}")

        # Sanity: high < low
        bad_hl = c.execute("SELECT COUNT(*) FROM daily_prices WHERE high < low").fetchone()[0]
        print(f"  high<low={bad_hl} {'✅' if bad_hl==0 else '❌'}")

        # Sanity: zero volume
        zero_vol = c.execute("SELECT COUNT(*) FROM daily_prices WHERE volume <= 0").fetchone()[0]
        print(f"  volume≤0={zero_vol} {'✅' if zero_vol==0 else '⚠️ ' + str(zero_vol) + ' rows'}")

        # Sanity: extreme daily change (>20%)
        extreme = c.execute("""
            SELECT COUNT(*) FROM (
                SELECT code, trade_date, close,
                       LAG(close) OVER (PARTITION BY code ORDER BY trade_date) AS prev
                FROM daily_prices
            ) WHERE prev IS NOT NULL AND prev > 0
              AND ABS((close - prev) / prev) > 0.20
        """).fetchone()[0]
        ok = extreme < total * 10  # ~10% of stocks having one extreme day is OK
        print(f"  单日涨跌>20%={extreme}条 {'✅' if ok else '⚠️'}")

        # 数据新鲜度
        latest_date = c.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()[0]
        from datetime import date
        today = date.today().isoformat()
        print(f"  最新日期={latest_date} (今天={today})")

        # ============================================
        # 3. fundamentals 基本面
        # ============================================
        print("\n=== fundamentals ===")
        fund_total = c.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0]
        rev = c.execute("SELECT COUNT(*) FROM fundamentals WHERE revenue IS NOT NULL").fetchone()[0]
        profit = c.execute("SELECT COUNT(*) FROM fundamentals WHERE net_profit IS NOT NULL").fetchone()[0]
        roe = c.execute("SELECT COUNT(*) FROM fundamentals WHERE roe IS NOT NULL").fetchone()[0]

        print(f"  总数={fund_total}")
        print(f"  有营收={rev} ({round(rev/fund_total*100,1) if fund_total>0 else 0}%)")
        print(f"  有利润={profit} ({round(profit/fund_total*100,1) if fund_total>0 else 0}%)")
        print(f"  有ROE={roe} ({round(roe/fund_total*100,1) if fund_total>0 else 0}%)")
        ok = rev / fund_total > 0.95 if fund_total > 0 else False
        print(f"  营收覆盖率 {'✅' if ok else '❌ (<95%)'}")
        if not ok: failures += 1

        # Sanity: negative revenue (rare but possible for small caps)
        neg_rev = c.execute("SELECT COUNT(*) FROM fundamentals WHERE revenue IS NOT NULL AND revenue < 0").fetchone()[0]
        print(f"  负营收={neg_rev} {'⚠️' if neg_rev>0 else '✅'}")

        # Sanity: ROE extremes
        roe_extreme = c.execute("SELECT COUNT(*) FROM fundamentals WHERE roe IS NOT NULL AND (roe < -100 OR roe > 100)").fetchone()[0]
        print(f"  ROE极端值(<-100 or >100)={roe_extreme} {'⚠️' if roe_extreme>0 else '✅'}")

        # ============================================
        # 4. factors 因子评分
        # ============================================
        print("\n=== factors ===")
        fac_total = c.execute("SELECT COUNT(*) FROM factors").fetchone()[0]
        mn = c.execute("SELECT MIN(total_score) FROM factors").fetchone()[0]
        mx = c.execute("SELECT MAX(total_score) FROM factors").fetchone()[0]
        print(f"  总数={fac_total}, 总分范围={mn:.1f}~{mx:.1f}")
        ok = 20 <= mx <= 120
        print(f"  总分范围 {'✅' if ok else '❌ (异常)'}")
        if not ok: failures += 1

        # ============================================
        # 5. cross-source 交叉验证
        # ============================================
        print("\n=== 交叉验证 ===")
        # Compare stocks count: stocks table vs fundamentals
        stock_count = c.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
        diff = abs(stock_count - fund_total)
        print(f"  stocks={stock_count}, fundamentals={fund_total}, 差异={diff} {'✅' if diff<50 else '⚠️'}")

    # ============================================
    # Report
    # ============================================
    print(f"\n{'='*40}")
    if failures == 0:
        print("  数据质量检查通过 ✅")
    else:
        print(f"  数据质量问题: {failures} 项 ❌")
    print(f"{'='*40}")

    write_json_log(
        file_name="worker.log", level="WARN" if failures > 0 else "INFO",
        module="validate_data", message=f"data quality check: {failures} failures",
        context={"failures": failures},
    )

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
