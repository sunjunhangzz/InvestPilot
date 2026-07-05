"use client";

import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { CandlestickChart, BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([CandlestickChart, BarChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer]);

type OHLC = { date: string; open: number; high: number; low: number; close: number; volume: number };
type Period = "daily" | "weekly" | "monthly";

export default function PriceChart({ code }: { code: string }) {
  const [data, setData] = useState<OHLC[]>([]);
  const [period, setPeriod] = useState<Period>("daily");
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    let c = false;
    async function f() {
      try {
        const r = await fetch(`/api/stocks/${code}/prices?days=180&period=${period}`);
        const j = await r.json();
        if (!c && j.ok) setData(j.data.prices ?? []);
      } catch { /* offline */ }
    }
    f();
    return () => { c = true; };
  }, [code, period]);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current, undefined, { renderer: "canvas" });
    }

    const dates = data.map((d) => d.date);
    const ohlc = data.map((d) => [d.open, d.close, d.low, d.high]);
    const volumes = data.map((d) => d.volume);
    const upColor = "#ef4444";
    const downColor = "#22c55e";

    chartRef.current.setOption(
      {
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "cross" },
          formatter: (params: unknown) => {
            const items = params as Array<{ seriesName: string; value: unknown; axisValue: string }>;
            if (!items?.length) return "";
            let tip = `<strong>${items[0].axisValue}</strong><br/>`;
            for (const item of items) {
              if (item.seriesName === "K线") {
                const v = item.value as number[];
                tip += `开: ${v[1]}<br/>收: ${v[2]}<br/>低: ${v[3]}<br/>高: ${v[0]}<br/>`;
              } else if (item.seriesName === "成交量") {
                const v = item.value as number;
                tip += `成交量: ${(v / 10000).toFixed(0)} 万手`;
              }
            }
            return tip;
          },
        },
        grid: [
          { left: 60, right: 20, top: 40, height: "52%" },
          { left: 60, right: 20, top: "74%", height: "20%" },
        ],
        xAxis: [
          { type: "category", data: dates, gridIndex: 0, axisLabel: { show: false }, axisLine: { onZero: false } },
          { type: "category", data: dates, gridIndex: 1, axisLabel: { rotate: 30, fontSize: 10 } },
        ],
        yAxis: [
          { type: "value", gridIndex: 0, scale: true, splitArea: { show: true } },
          {
            type: "value", gridIndex: 1,
            axisLabel: { formatter: (v: number) => (v / 10000).toFixed(0) + "万" },
          },
        ],
        series: [
          {
            name: "K线",
            type: "candlestick",
            data: ohlc,
            itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor },
            xAxisIndex: 0, yAxisIndex: 0,
          },
          {
            name: "成交量",
            type: "bar",
            data: volumes,
            barWidth: "60%",
            itemStyle: {
              color: (p: { dataIndex: number }) =>
                ohlc[p.dataIndex][1] >= ohlc[p.dataIndex][0] ? upColor : downColor,
            },
            xAxisIndex: 1, yAxisIndex: 1,
          },
        ],
        dataZoom: [
          { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
          { type: "slider", xAxisIndex: [0, 1], start: 0, end: 100, height: 20, bottom: 0 },
        ],
      },
      { notMerge: true },
    );

    const observer = new ResizeObserver(() => chartRef.current?.resize());
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [data]);

  useEffect(() => {
    return () => { chartRef.current?.dispose(); chartRef.current = null; };
  }, []);

  const tabClass = (p: Period) =>
    `px-3 py-1 text-xs rounded ${period === p ? "bg-[var(--accent)] text-white" : "bg-gray-100 text-[var(--muted)]"}`;

  return (
    <div>
      <div className="mb-2 flex gap-1">
        <button className={tabClass("daily")} onClick={() => setPeriod("daily")}>日K</button>
        <button className={tabClass("weekly")} onClick={() => setPeriod("weekly")}>周K</button>
        <button className={tabClass("monthly")} onClick={() => setPeriod("monthly")}>月K</button>
      </div>
      {data.length === 0 ? (
        <div className="flex h-80 items-center justify-center rounded-lg border border-[var(--line)] bg-white text-sm text-[var(--muted)]">暂无行情数据</div>
      ) : (
        <div ref={containerRef} className="h-[32rem] w-full rounded-lg border border-[var(--line)] bg-white" />
      )}
    </div>
  );
}
