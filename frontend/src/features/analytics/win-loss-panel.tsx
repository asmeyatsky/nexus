import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { analyticsApi } from "./analytics-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function WinLossPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "win-loss"],
    queryFn: () => analyticsApi.winLoss(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const monthData = Object.entries(data.by_month as Record<string, { won: number; lost: number; won_amount: number; lost_amount: number }>)
    .map(([month, vals]) => ({ month, ...vals }));

  const sourceData = Object.entries(data.by_source as Record<string, { won: number; lost: number }>)
    .map(([source, vals]) => ({ source: formatLabel(source), ...vals }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Win Rate</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.win_rate}%</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Deal Cycle</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.avg_cycle_days} days</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Won Amount</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.avg_won_amount).toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Lost Amount</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${Math.round(data.avg_lost_amount).toLocaleString()}</div></CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Won vs Lost Over Time</CardTitle></CardHeader>
          <CardContent>
            {monthData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={monthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" /><YAxis /><Tooltip /><Legend />
                  <Bar dataKey="won" fill="#10b981" name="Won" />
                  <Bar dataKey="lost" fill="#ef4444" name="Lost" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No data</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>By Source</CardTitle></CardHeader>
          <CardContent>
            {sourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={sourceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="source" /><YAxis /><Tooltip /><Legend />
                  <Bar dataKey="won" fill="#10b981" name="Won" />
                  <Bar dataKey="lost" fill="#ef4444" name="Lost" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No data</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
