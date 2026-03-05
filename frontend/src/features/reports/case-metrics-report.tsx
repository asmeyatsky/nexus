import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { reportsApi } from "./reports-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1"];

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function CaseMetricsReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "case-metrics"],
    queryFn: () => reportsApi.caseMetrics(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const statusData = Object.entries(data.by_status as Record<string, number>).map(([status, count]) => ({
    name: formatLabel(status),
    value: count,
  }));

  const priorityData = Object.entries(data.by_priority as Record<string, number>).map(([priority, count]) => ({
    priority: formatLabel(priority),
    count,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Open</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.open_count}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Resolved</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.resolved_count}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Closed</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.closed_count}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Resolution</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.avg_resolution_hours}h</div></CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Cases by Status</CardTitle></CardHeader>
          <CardContent>
            {statusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={statusData} cx="50%" cy="50%" outerRadius={100} innerRadius={50} dataKey="value" label>
                    {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No data</p>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Cases by Priority</CardTitle></CardHeader>
          <CardContent>
            {priorityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={priorityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="priority" /><YAxis />
                  <Tooltip /><Bar dataKey="count" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No data</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
