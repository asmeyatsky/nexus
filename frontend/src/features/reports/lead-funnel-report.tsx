import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { reportsApi } from "./reports-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1"];

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function LeadFunnelReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "lead-funnel"],
    queryFn: () => reportsApi.leadFunnel(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const chartData = Object.entries(data.by_status as Record<string, number>).map(([status, count]) => ({
    name: formatLabel(status),
    value: count,
  }));

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Leads</CardTitle></CardHeader>
        <CardContent><div className="text-2xl font-bold">{data.total}</div></CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Leads by Status</CardTitle></CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie data={chartData} cx="50%" cy="50%" outerRadius={120} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-center py-8">No lead data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
