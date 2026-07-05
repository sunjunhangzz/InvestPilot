"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

type Point = { day: number; avgReturn: number | null };

export default function DecayChart({ data }: { data: Point[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const cr = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    if (!cr.current) cr.current = echarts.init(ref.current);

    const days = data.map((d) => d.day);
    const vals = data.map((d) => d.avgReturn ?? 0);

    cr.current.setOption({
      tooltip: { trigger: "axis", formatter: (p: unknown) => { const items = p as Array<{ axisValue: string; value: number }>; return `${items[0]?.axisValue}日：${items[0]?.value?.toFixed(2)}%`; } },
      xAxis: { type: "category", data: days, name: "持有天数" },
      yAxis: { type: "value", name: "累计收益(%)", axisLabel: { formatter: "{value}%" } },
      series: [{
        type: "line", data: vals, smooth: true, symbol: "circle",
        lineStyle: { color: "#2563eb" },
        markLine: { data: [{ yAxis: 0, lineStyle: { color: "#9ca3af", type: "dashed" } }], silent: true },
      }],
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
    }, { notMerge: true });

    const o = new ResizeObserver(() => cr.current?.resize());
    o.observe(ref.current);
    return () => o.disconnect();
  }, [data]);

  useEffect(() => { return () => { cr.current?.dispose(); cr.current = null; }; }, []);

  return <div ref={ref} className="h-64 w-full rounded-lg border border-[var(--line)] bg-white" />;
}
