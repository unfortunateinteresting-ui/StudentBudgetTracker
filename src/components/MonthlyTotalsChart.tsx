import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";

import { currency } from "../lib/format";
import type { MonthlySeriesPoint } from "../lib/types";
import styles from "./Charts.module.css";

interface MonthlyTotalsChartProps {
  data: MonthlySeriesPoint[];
}

const rowHeight = 48;

const monthLabel = (monthKey: string) => {
  const [year, month] = monthKey.split("-").map(Number);
  if (!year || !month) return monthKey;
  return new Intl.DateTimeFormat("en-US", { month: "short" }).format(
    new Date(year, month - 1, 1),
  );
};

export function MonthlyTotalsChart({ data }: MonthlyTotalsChartProps) {
  if (!data.length) {
    return <div className={styles.chartEmpty}>No chart data available.</div>;
  }

  const chartData = data.map((item) => {
    if (item.phase === "future") {
      return {
        ...item,
        primaryLabel: "Planned",
        primaryValue: item.planned_spend,
        primaryColor: "var(--color-planned)",
        secondaryLabel: "Predicted",
        secondaryValue: item.predicted_spend,
        secondaryColor: "var(--color-predicted)",
      };
    }

    return {
      ...item,
      primaryLabel: "Spent",
      primaryValue: item.gross_spend,
      primaryColor: "var(--color-clay)",
      secondaryLabel: "After income/credits",
      secondaryValue: item.actual_spend,
      secondaryColor:
        item.phase === "current" ? "var(--color-current)" : "var(--color-forest)",
    };
  });

  const plotHeight = Math.max(220, chartData.length * rowHeight + 24);
  const margin = { top: 8, right: 126, bottom: 8, left: 72 };

  return (
    <div className={styles.chartShell}>
      <div className={styles.plotArea} style={{ height: `${plotHeight}px` }}>
        <ParentSize>
          {({ width }) => {
            if (!width) return null;

            const innerWidth = Math.max(width - margin.left - margin.right, 140);
            const innerHeight = Math.max(plotHeight - margin.top - margin.bottom, 160);
            const maxValue = Math.max(
              ...chartData.flatMap((item) => [item.primaryValue, item.secondaryValue]),
              1,
            );
            const xScale = scaleLinear({
              domain: [0, maxValue * 1.15],
              range: [0, innerWidth],
              nice: true,
            });
            const yScale = scaleBand<string>({
              domain: chartData.map((item) => item.month_key),
              range: [0, innerHeight],
              padding: 0.3,
            });

            return (
              <svg height={plotHeight} width={width}>
                <Group left={margin.left} top={margin.top}>
                  {chartData.map((item) => {
                    const bandY = yScale(item.month_key) ?? 0;
                    const bandHeight = yScale.bandwidth();
                    const primaryWidth = Math.max(xScale(item.primaryValue), 0);
                    const secondaryWidth = Math.max(xScale(item.secondaryValue), 0);
                    const valueX = Math.min(Math.max(primaryWidth, secondaryWidth) + 8, innerWidth);

                    return (
                      <g key={item.month_key}>
                        <rect
                          fill="rgba(23, 25, 20, 0.06)"
                          height={bandHeight}
                          rx={10}
                          width={innerWidth}
                          x={0}
                          y={bandY}
                        />
                        <Bar
                          fill={item.primaryColor}
                          height={bandHeight}
                          opacity={0.74}
                          rx={10}
                          width={primaryWidth}
                          x={0}
                          y={bandY}
                        />
                        <Bar
                          fill={item.secondaryColor}
                          height={Math.max(bandHeight * 0.48, 8)}
                          rx={8}
                          width={secondaryWidth}
                          x={0}
                          y={bandY + bandHeight * 0.26}
                        />
                        <text
                          dy="0.35em"
                          fill="var(--color-chart-label)"
                          fontFamily="IBM Plex Sans"
                          fontSize={11}
                          fontWeight={600}
                          textAnchor="end"
                          x={-10}
                          y={bandY + bandHeight / 2}
                        >
                          {monthLabel(item.month_key)}
                        </text>
                        <text
                          dy="0.35em"
                          fill="var(--color-chart-label)"
                          fontFamily="IBM Plex Sans"
                          fontSize={11}
                          fontWeight={600}
                          x={valueX}
                          y={bandY + bandHeight / 2}
                        >
                          {currency(item.secondaryValue)} / {currency(item.primaryValue)}
                        </text>
                      </g>
                    );
                  })}
                </Group>
              </svg>
            );
          }}
        </ParentSize>
      </div>
      <div className={styles.legend}>
        {[
          { label: "Spent", color: "var(--color-clay)" },
          { label: "After income/credits", color: "var(--color-forest)" },
          { label: "Current month", color: "var(--color-current)" },
          { label: "Planned future", color: "var(--color-planned)" },
          { label: "Predicted future", color: "var(--color-predicted)" },
        ].map((item) => (
          <span className={styles.legendItem} key={item.label}>
            <span className={styles.swatch} style={{ background: item.color }} />
            <span className={styles.legendText}>{item.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
