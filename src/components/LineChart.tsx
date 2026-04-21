import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleBand, scaleLinear } from "@visx/scale";
import { LinePath } from "@visx/shape";

import { currency } from "../lib/format";
import type { MonthlySeriesPoint } from "../lib/types";
import styles from "./Charts.module.css";

const margin = { top: 20, right: 16, bottom: 40, left: 56 };

interface LineChartProps {
  data: MonthlySeriesPoint[];
}

const monthTickLabel = (monthKey: string) => {
  const [year, month] = monthKey.split("-").map(Number);
  if (!year || !month) return monthKey;
  return new Intl.DateTimeFormat("en-US", { month: "short" }).format(
    new Date(year, month - 1, 1),
  );
};

export function LineChart({ data }: LineChartProps) {
  if (!data.length) {
    return <div className={styles.chartEmpty}>No chart data available.</div>;
  }

  const tickLegend = [
    { label: "Spent", color: "var(--color-clay)" },
    { label: "Cap", color: "var(--color-forest)" },
    { label: "Balance", color: "var(--color-ink)" },
  ];

  return (
    <div className={styles.chartShell}>
      <div className={styles.plotArea}>
        <ParentSize>
          {({ width, height }) => {
            const innerWidth = Math.max(width - margin.left - margin.right, 140);
            const innerHeight = Math.max(height - margin.top - margin.bottom, 140);
            const maxValue = Math.max(
              ...data.flatMap((item) => [item.spent, item.cap, item.runway_balance]),
              1,
            );

            const xScale = scaleBand<string>({
              domain: data.map((item) => item.month_key),
              range: [0, innerWidth],
              padding: 0.32,
            });

            const yScale = scaleLinear<number>({
              domain: [0, maxValue * 1.15],
              range: [innerHeight, 0],
              nice: true,
            });

            const centers = data.map(
              (item) => (xScale(item.month_key) || 0) + xScale.bandwidth() / 2,
            );
            const perMonthWidth = innerWidth / Math.max(data.length, 1);
            const tickStep = perMonthWidth < 54 ? 3 : perMonthWidth < 76 ? 2 : 1;
            const tickValues = data
              .filter((_, index) => index % tickStep === 0)
              .map((item) => item.month_key);

            return (
              <svg height={height} width={width}>
                <Group left={margin.left} top={margin.top}>
                  <GridRows
                    height={innerHeight}
                    scale={yScale}
                    stroke="rgba(22, 24, 19, 0.08)"
                    width={innerWidth}
                  />
                  <LinePath
                    data={data}
                    stroke="var(--color-clay)"
                    strokeWidth={3}
                    x={(_, index) => centers[index]}
                    y={(item) => yScale(item.spent)}
                  />
                  <LinePath
                    data={data}
                    stroke="var(--color-forest)"
                    strokeWidth={3}
                    x={(_, index) => centers[index]}
                    y={(item) => yScale(item.cap)}
                  />
                  <LinePath
                    data={data}
                    stroke="var(--color-ink)"
                    strokeDasharray="5 6"
                    strokeWidth={2}
                    x={(_, index) => centers[index]}
                    y={(item) => yScale(item.runway_balance)}
                  />
                  {data.map((item, index) => (
                    <g key={item.month_key}>
                      <circle
                        cx={centers[index]}
                        cy={yScale(item.spent)}
                        fill="var(--color-clay)"
                        r={3.2}
                      />
                      <circle
                        cx={centers[index]}
                        cy={yScale(item.cap)}
                        fill="var(--color-forest)"
                        r={3.2}
                      />
                      <circle
                        cx={centers[index]}
                        cy={yScale(item.runway_balance)}
                        fill="var(--color-ink)"
                        r={2.8}
                      />
                    </g>
                  ))}
                  <AxisLeft
                    numTicks={4}
                    scale={yScale}
                    tickFormat={(value) => currency(Number(value))}
                    tickLabelProps={() => ({
                      fill: "rgba(22, 24, 19, 0.7)",
                      fontFamily: "IBM Plex Sans",
                      fontSize: 11,
                      textAnchor: "end",
                      dx: -4,
                    })}
                  />
                  <AxisBottom
                    scale={xScale}
                    tickFormat={(value) => monthTickLabel(String(value))}
                    tickLabelProps={() => ({
                      fill: "rgba(22, 24, 19, 0.7)",
                      fontFamily: "IBM Plex Sans",
                      fontSize: 9,
                      textAnchor: "middle",
                    })}
                    tickValues={tickValues}
                    top={innerHeight}
                  />
                </Group>
              </svg>
            );
          }}
        </ParentSize>
      </div>
      <div className={styles.legend}>
        {tickLegend.map((item) => (
          <span className={styles.legendItem} key={item.label}>
            <span className={styles.swatch} style={{ background: item.color }} />
            <span className={styles.legendText}>{item.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
