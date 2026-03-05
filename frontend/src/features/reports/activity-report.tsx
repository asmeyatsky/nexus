import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { reportsApi } from "./reports-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ENTITY_COLORS: Record<string, string> = {
  accounts: "#3b82f6",
  contacts: "#10b981",
  opportunities: "#f59e0b",
  leads: "#8b5cf6",
  cases: "#ef4444",
};

export function ActivityReport() {
  const [period, setPeriod] = useState("day");

  const { data, isLoading } = useQuery({
    queryKey: ["reports", "activity-summary", period],
    queryFn: () => reportsApi.activitySummary(period),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const allDates = new Set<string>();
  for (const entityData of Object.values(data as Record<string, Record<string, number>>)) {
    for (const date of Object.keys(entityData)) {
      allDates.add(date);
    }
  }

  const chartData = [...allDates].sort().map((date) => {
    const point: Record<string, string | number> = { date };
    for (const [entity, entityData] of Object.entries(data as Record<string, Record<string, number>>)) {
      point[entity] = entityData[date] ?? 0;
    }
    return point;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Period:</span>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[120px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="day">Daily</SelectItem>
            <SelectItem value="week">Weekly</SelectItem>
            <SelectItem value="month">Monthly</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader><CardTitle>Entity Creation Over Time</CardTitle></CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis />
                <Tooltip />
                <Legend />
                {Object.entries(ENTITY_COLORS).map(([entity, color]) => (
                  <Line key={entity} type="monotone" dataKey={entity} stroke={color} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-center py-8">No activity data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
