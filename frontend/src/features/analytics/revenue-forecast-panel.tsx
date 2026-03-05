import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { analyticsApi } from "./analytics-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function RevenueForecastPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "revenue-forecast"],
    queryFn: () => analyticsApi.revenueForecast(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const monthData = Object.entries(data.by_month as Record<string, { weighted: number; total: number; count: number }>).map(
    ([month, vals]) => ({
      month,
      total: Math.round(vals.total),
      weighted: Math.round(vals.weighted),
      count: vals.count,
    })
  );

  const stageData = Object.entries(data.by_stage as Record<string, { count: number; total: number; weighted: number }>).map(
    ([stage, vals]) => ({
      stage: formatLabel(stage),
      count: vals.count,
      total: Math.round(vals.total),
      weighted: Math.round(vals.weighted),
    })
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Weighted Pipeline</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.weighted_pipeline).toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Best Case</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.best_case).toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Committed</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.committed).toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Closed Won</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.closed_won_total).toLocaleString()}</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Forecast by Month</CardTitle></CardHeader>
        <CardContent>
          {monthData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={monthData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" /><YAxis />
                <Tooltip formatter={(v) => `$${Number(v ?? 0).toLocaleString()}`} />
                <Bar dataKey="total" fill="#3b82f6" name="Total" />
                <Bar dataKey="weighted" fill="#10b981" name="Weighted" />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-center py-8">No forecast data</p>}
        </CardContent>
      </Card>

      {stageData.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Stage Breakdown</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b">
                  <th className="text-left py-2">Stage</th>
                  <th className="text-right py-2">Count</th>
                  <th className="text-right py-2">Total</th>
                  <th className="text-right py-2">Weighted</th>
                </tr></thead>
                <tbody>{stageData.map((r) => (
                  <tr key={r.stage} className="border-b">
                    <td className="py-2">{r.stage}</td>
                    <td className="text-right py-2">{r.count}</td>
                    <td className="text-right py-2">${r.total.toLocaleString()}</td>
                    <td className="text-right py-2">${r.weighted.toLocaleString()}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
