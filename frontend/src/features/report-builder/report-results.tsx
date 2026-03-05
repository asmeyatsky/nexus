import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1", "#ec4899", "#14b8a6"];

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface ReportResultsProps {
  data: unknown;
  chartType: "table" | "bar" | "pie" | "line";
  groupBy?: string;
}

export function ReportResults({ data, chartType, groupBy }: ReportResultsProps) {
  if (!data) return null;

  const result = data as { type: string; data: unknown; total: number };

  if (result.type === "aggregated") {
    const aggData = result.data as Record<string, { count: number; items: Record<string, unknown>[] }>;
    const chartData = Object.entries(aggData).map(([key, val]) => ({
      name: formatLabel(key),
      count: val.count,
    }));

    if (chartType === "bar") {
      return (
        <Card>
          <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" /><YAxis /><Tooltip />
                <Bar dataKey="count" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      );
    }

    if (chartType === "pie") {
      return (
        <Card>
          <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie data={chartData} cx="50%" cy="50%" outerRadius={120} dataKey="count" label>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip /><Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      );
    }

    if (chartType === "line") {
      return (
        <Card>
          <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" /><YAxis /><Tooltip />
                <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      );
    }

    // Table for aggregated
    return (
      <Card>
        <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-auto max-h-[500px]">
            {Object.entries(aggData).map(([key, val]) => (
              <div key={key} className="mb-4">
                <h4 className="font-medium mb-2">{formatLabel(key)} ({val.count})</h4>
                <RenderTable rows={val.items} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Tabular results
  const rows = result.data as Record<string, unknown>[];

  if (chartType !== "table" && groupBy) {
    // Can't chart ungrouped tabular data meaningfully, show table
  }

  if (chartType === "table" || !groupBy) {
    return (
      <Card>
        <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
        <CardContent>
          <RenderTable rows={rows} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader><CardTitle>Results ({result.total} total)</CardTitle></CardHeader>
      <CardContent><RenderTable rows={rows} /></CardContent>
    </Card>
  );
}

function RenderTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows || rows.length === 0) return <p className="text-muted-foreground text-center py-4">No results</p>;

  const headers = Object.keys(rows[0]);

  return (
    <div className="overflow-auto max-h-[500px]">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-background">
          <tr className="border-b">
            {headers.map((h) => (
              <th key={h} className="text-left py-2 px-2 whitespace-nowrap">{formatLabel(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b">
              {headers.map((h) => (
                <td key={h} className="py-2 px-2 whitespace-nowrap">{String(row[h] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
