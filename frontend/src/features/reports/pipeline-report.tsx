import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { reportsApi } from "./reports-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function PipelineReport() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "pipeline-summary"],
    queryFn: () => reportsApi.pipelineSummary(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const chartData = Object.entries(data.by_stage as Record<string, { count: number; total: number; weighted: number }>).map(
    ([stage, vals]) => ({
      stage: formatLabel(stage),
      total: Math.round(vals.total),
      weighted: Math.round(vals.weighted),
      count: vals.count,
    })
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Pipeline Value</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${data.total_pipeline_value.toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Weighted Pipeline</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">${data.total_weighted_pipeline.toLocaleString()}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Won / Lost / Open</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.won_count} / {data.lost_count} / {data.open_count}</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Pipeline by Stage</CardTitle></CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="stage" angle={-20} textAnchor="end" height={80} fontSize={12} />
                <YAxis />
                <Tooltip formatter={(v) => `$${Number(v ?? 0).toLocaleString()}`} />
                <Bar dataKey="total" fill="#3b82f6" name="Total" />
                <Bar dataKey="weighted" fill="#10b981" name="Weighted" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-center py-8">No pipeline data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
