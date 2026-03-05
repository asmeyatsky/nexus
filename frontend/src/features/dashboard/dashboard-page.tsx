import { useQuery } from "@tanstack/react-query";
import { Building2, TrendingUp, Headphones, UserPlus } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { reportsApi } from "@/features/reports/reports-api";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "./stat-card";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1"];

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function DashboardPage() {
  const pipeline = useQuery({
    queryKey: ["reports", "pipeline-summary"],
    queryFn: () => reportsApi.pipelineSummary(),
  });
  const funnel = useQuery({
    queryKey: ["reports", "lead-funnel"],
    queryFn: () => reportsApi.leadFunnel(),
  });
  const cases = useQuery({
    queryKey: ["reports", "case-metrics"],
    queryFn: () => reportsApi.caseMetrics(),
  });

  const isLoading = pipeline.isLoading || funnel.isLoading || cases.isLoading;
  if (isLoading) return <LoadingSpinner />;

  const pipelineData = pipeline.data;
  const funnelData = funnel.data;
  const caseData = cases.data;

  const stageChartData = pipelineData
    ? Object.entries(pipelineData.by_stage as Record<string, { count: number; total: number; weighted: number }>).map(
        ([stage, vals]) => ({ stage: formatLabel(stage), total: Math.round(vals.total), weighted: Math.round(vals.weighted) })
      )
    : [];

  const funnelChartData = funnelData
    ? Object.entries(funnelData.by_status as Record<string, number>).map(([status, count]) => ({
        name: formatLabel(status),
        value: count,
      }))
    : [];

  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of your CRM" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <StatCard title="Pipeline Value" value={`$${Math.round(pipelineData?.total_pipeline_value ?? 0).toLocaleString()}`} icon={TrendingUp} />
        <StatCard title="Open Opportunities" value={pipelineData?.open_count ?? 0} icon={Building2} />
        <StatCard title="Active Leads" value={funnelData?.total ?? 0} icon={UserPlus} />
        <StatCard title="Open Cases" value={caseData?.open_count ?? 0} icon={Headphones} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2 mb-6">
        <Card>
          <CardHeader><CardTitle>Pipeline by Stage</CardTitle></CardHeader>
          <CardContent>
            {stageChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stageChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="stage" angle={-20} textAnchor="end" height={80} fontSize={11} />
                  <YAxis /><Tooltip formatter={(v) => `$${Number(v ?? 0).toLocaleString()}`} />
                  <Bar dataKey="total" fill="#3b82f6" name="Total" />
                  <Bar dataKey="weighted" fill="#10b981" name="Weighted" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No pipeline data</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Lead Funnel</CardTitle></CardHeader>
          <CardContent>
            {funnelChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={funnelChartData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label>
                    {funnelChartData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-8">No lead data</p>}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Cases Resolved</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{caseData?.resolved_count ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Resolution Time</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{caseData?.avg_resolution_hours ?? 0}h</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Won / Lost</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{pipelineData?.won_count ?? 0} / {pipelineData?.lost_count ?? 0}</div></CardContent>
        </Card>
      </div>
    </div>
  );
}
