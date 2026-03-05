import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from "recharts";
import { analyticsApi } from "./analytics-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const GROUP_FIELDS: Record<string, { value: string; label: string }[]> = {
  accounts: [{ value: "industry", label: "Industry" }, { value: "territory", label: "Territory" }],
  contacts: [],
  opportunities: [{ value: "stage", label: "Stage" }],
  leads: [{ value: "status", label: "Status" }, { value: "rating", label: "Rating" }],
  cases: [{ value: "status", label: "Status" }, { value: "priority", label: "Priority" }],
};

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#6366f1", "#ec4899", "#14b8a6"];

export function TrendsPanel() {
  const [entity, setEntity] = useState("opportunities");
  const [period, setPeriod] = useState("month");
  const [groupBy, setGroupBy] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "trends", entity, period, groupBy],
    queryFn: () => analyticsApi.trends(entity, period, groupBy || undefined),
  });

  if (isLoading) return <LoadingSpinner />;

  const availableGroups = GROUP_FIELDS[entity] ?? [];

  let chartData: Record<string, string | number>[] = [];
  let groupKeys: string[] = [];

  if (data?.grouped) {
    const allKeys = new Set<string>();
    for (const vals of Object.values(data.data as Record<string, Record<string, number>>)) {
      for (const k of Object.keys(vals)) allKeys.add(k);
    }
    groupKeys = [...allKeys];
    chartData = Object.entries(data.data as Record<string, Record<string, number>>).map(([date, vals]) => {
      const point: Record<string, string | number> = { date };
      for (const k of groupKeys) point[k] = vals[k] ?? 0;
      return point;
    });
  } else if (data) {
    chartData = Object.entries(data.data as Record<string, number>).map(([date, count]) => ({ date, count }));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={entity} onValueChange={(v) => { setEntity(v); setGroupBy(""); }}>
          <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="accounts">Accounts</SelectItem>
            <SelectItem value="contacts">Contacts</SelectItem>
            <SelectItem value="opportunities">Opportunities</SelectItem>
            <SelectItem value="leads">Leads</SelectItem>
            <SelectItem value="cases">Cases</SelectItem>
          </SelectContent>
        </Select>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="day">Daily</SelectItem>
            <SelectItem value="week">Weekly</SelectItem>
            <SelectItem value="month">Monthly</SelectItem>
          </SelectContent>
        </Select>
        {availableGroups.length > 0 && (
          <Select value={groupBy || "none"} onValueChange={(v) => setGroupBy(v === "none" ? "" : v)}>
            <SelectTrigger className="w-[140px]"><SelectValue placeholder="Group by" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">No grouping</SelectItem>
              {availableGroups.map((g) => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      <Card>
        <CardHeader><CardTitle>Trends</CardTitle></CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              {data?.grouped ? (
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} /><YAxis /><Tooltip /><Legend />
                  {groupKeys.map((key, i) => (
                    <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} stackId="a" />
                  ))}
                </BarChart>
              ) : (
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} /><YAxis /><Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} />
                </LineChart>
              )}
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-center py-8">No trend data available</p>}
        </CardContent>
      </Card>
    </div>
  );
}
