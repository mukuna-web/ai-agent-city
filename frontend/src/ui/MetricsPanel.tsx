import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useSimulationStore, type MetricsData } from '../store/simulation';

export function MetricsPanel() {
  const metricsHistory = useSimulationStore((s) => s.metricsHistory);
  const metrics = useSimulationStore((s) => s.metrics);

  // Downsample history for performance (max 100 data points)
  const chartData = useMemo(() => {
    if (metricsHistory.length <= 100) return metricsHistory;
    const step = Math.ceil(metricsHistory.length / 100);
    return metricsHistory.filter((_, i) => i % step === 0);
  }, [metricsHistory]);

  return (
    <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-10 w-[900px] max-w-[95vw]">
        <div className="glass-card p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs uppercase tracking-widest text-white/50 font-semibold">
            Economic Dashboard
          </h3>
          <div className="flex items-center gap-4">
            <QuickStat label="GDP" value={`$${formatNumber(metrics.gdp)}`} color="text-emerald-400" />
            <QuickStat
              label="Unemploy"
              value={`${(metrics.unemployment * 100).toFixed(1)}%`}
              color="text-rose-400"
            />
            <button
              type="button"
              onClick={() => downloadMetricsCsv(metricsHistory)}
              disabled={metricsHistory.length === 0}
              className="rounded border border-white/15 px-2 py-1 text-[10px] text-white/60 disabled:opacity-30"
            >
              Export CSV
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded border border-white/15 px-2 py-1 text-[10px] text-white/60"
            >
              Print / PDF
            </button>
            <QuickStat label="Gini" value={metrics.gini.toFixed(3)} color="text-amber-400" />
            <QuickStat
              label="Avg Wage"
              value={`$${formatNumber(metrics.avgWage)}`}
              color="text-sky-400"
            />
          </div>
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-3 gap-4">
          <ChartCard title="GDP" color="#4ade80" dataKey="gdp" data={chartData} />
          <ChartCard
            title="Unemployment"
            color="#f87171"
            dataKey="unemployment"
            data={chartData}
            isPercent
          />
          <ChartCard title="Gini Coefficient" color="#fbbf24" dataKey="gini" data={chartData} />
        </div>
      </div>
    </div>
  );
}

function downloadMetricsCsv(history: MetricsData[]) {
  if (history.length === 0) return;
  const fields: (keyof MetricsData)[] = [
    'tick',
    'population',
    'gdp',
    'unemployment',
    'avgWage',
    'gini',
    'season',
  ];
  const escapeCell = (value: unknown) => {
    const text = String(value ?? '');
    return `"${text.replaceAll('"', '""')}"`;
  };
  const csv = [
    fields.join(','),
    ...history.map((row) => fields.map((field) => escapeCell(row[field])).join(',')),
  ].join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'ai-agent-city-metrics.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

interface ChartCardProps {
  title: string;
  color: string;
  dataKey: string;
  data: MetricsData[];
  isPercent?: boolean;
}

function ChartCard({ title, color, dataKey, data, isPercent }: ChartCardProps) {
  return (
    <div className="bg-white/5 rounded-lg p-3">
      <h4 className="text-[10px] uppercase tracking-wider text-white/40 mb-2">
        {title}
      </h4>
      <div className="h-28">
        {data.length < 2 ? (
          <div className="flex items-center justify-center h-full text-white/20 text-xs">
            Collecting data...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
              />
              <XAxis
                dataKey="tick"
                tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)' }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                tickLine={false}
                tickFormatter={(v: number) =>
                  isPercent ? `${(v * 100).toFixed(0)}%` : formatNumber(v)
                }
                width={40}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(0,0,0,0.8)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: 'white',
                }}
                formatter={(value: unknown) => {
                  const v = Number(value);
                  return isPercent
                    ? `${(v * 100).toFixed(1)}%`
                    : formatNumber(v);
                }}
                labelFormatter={(label: unknown) => `Tick ${label}`}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: color }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function QuickStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="text-right">
      <div className={`text-sm font-mono font-bold ${color}`}>{value}</div>
      <div className="text-[9px] uppercase tracking-wider text-white/30">
        {label}
      </div>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(0);
}
