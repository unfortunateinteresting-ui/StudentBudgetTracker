import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { Bar } from "@visx/shape";

import { currency } from "../lib/format";
import type { ChartPoint } from "../lib/types";
import styles from "./Charts.module.css";

interface BarChartProps {
  data: ChartPoint[];
  color?: string;
}

const rowHeight = 42;

const shortenLabel = (label: string, maxLength = 18) =>
  label.length <= maxLength ? label : `${label.slice(0, maxLength - 3)}...`;

export function BarChart({ data, color = "var(--color-clay)" }: BarChartProps) {
  if (!data.length) {
    return <div className={styles.chartEmpty}>No chart data available.</div>;
  }

  const plotHeight = Math.max(220, data.length * rowHeight + 24);
  const longestLabel = data.reduce((max, item) => Math.max(max, item.label.length), 0);
  const margin = {
    top: 8,
    right: 104,
    bottom: 8,
    left: Math.min(Math.max(longestLabel * 7 + 16, 96), 176),
  };

  return (
    <div className={styles.chartShell}>
      <div className={styles.plotArea} style={{ height: `${plotHeight}px` }}>
        <ParentSize>
          {({ width }) => {
            if (!width) return null;

            const innerWidth = Math.max(width - margin.left - margin.right, 140);
            const innerHeight = Math.max(plotHeight - margin.top - margin.bottom, 160);
            const xScale = scaleLinear({
              domain: [0, Math.max(...data.map((item) => item.value), 1) * 1.15],
              range: [0, innerWidth],
              nice: true,
            });
            const yScale = scaleBand<string>({
              domain: data.map((item) => item.label),
              range: [0, innerHeight],
              padding: 0.28,
            });

            return (
              <svg height={plotHeight} width={width}>
                <Group left={margin.left} top={margin.top}>
                  {data.map((item) => {
                    const bandY = yScale(item.label) ?? 0;
                    const bandHeight = yScale.bandwidth();
                    const barColor = item.color ?? color;
                    const barWidth = Math.max(xScale(item.value), 0);
                    const showInsideLabel = barWidth > innerWidth * 0.72;
                    const labelX = showInsideLabel
                      ? Math.max(barWidth - 8, 8)
                      : Math.min(barWidth + 8, innerWidth - 4);

                    return (
                      <g key={item.label}>
                        <rect
                          fill="rgba(23, 25, 20, 0.06)"
                          height={bandHeight}
                          rx={10}
                          width={innerWidth}
                          x={0}
                          y={bandY}
                        />
                        <Bar
                          fill={barColor}
                          height={bandHeight}
                          rx={10}
                          width={barWidth}
                          x={0}
                          y={bandY}
                        />
                        <text
                          dy="0.35em"
                          fill="var(--color-chart-label)"
                          fontFamily="IBM Plex Sans"
                          fontSize={11}
                          textAnchor="end"
                          x={-10}
                          y={bandY + bandHeight / 2}
                        >
                          {shortenLabel(item.label)}
                        </text>
                        <text
                          dy="0.35em"
                          fill={
                            showInsideLabel ? "var(--color-surface)" : "var(--color-chart-label)"
                          }
                          fontFamily="IBM Plex Sans"
                          fontSize={11}
                          fontWeight={600}
                          textAnchor={showInsideLabel ? "end" : "start"}
                          x={labelX}
                          y={bandY + bandHeight / 2}
                        >
                          {currency(item.value)}
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
    </div>
  );
}
