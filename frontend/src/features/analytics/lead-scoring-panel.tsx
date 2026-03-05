import { useQuery } from "@tanstack/react-query";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { analyticsApi } from "./analytics-api";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const COLORS = { hot: "#ef4444", warm: "#f59e0b", cold: "#3b82f6" };

export function LeadScoringPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "lead-scores"],
    queryFn: () => analyticsApi.leadScores(),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data) return null;

  const distData = Object.entries(data.distribution as Record<string, number>).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value,
  }));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Avg Score</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.avg_score}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Leads</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{data.total}</div></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Score Distribution</CardTitle></CardHeader>
          <CardContent>
            {distData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={distData} cx="50%" cy="50%" outerRadius={70} innerRadius={40} dataKey="value" label>
                    {distData.map((entry) => (
                      <Cell key={entry.name} fill={COLORS[entry.name.toLowerCase() as keyof typeof COLORS] ?? "#888"} />
                    ))}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-muted-foreground text-center py-4">No data</p>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Lead Scores</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-auto max-h-[400px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background"><tr className="border-b">
                <th className="text-left py-2">Name</th>
                <th className="text-left py-2">Company</th>
                <th className="text-left py-2">Status</th>
                <th className="text-left py-2">Rating</th>
                <th className="text-right py-2">Score</th>
              </tr></thead>
              <tbody>{(data.leads as Array<{ id: string; name: string; company: string; status: string; rating: string; score: number }>).map((lead) => (
                <tr key={lead.id} className="border-b">
                  <td className="py-2">{lead.name}</td>
                  <td className="py-2">{lead.company}</td>
                  <td className="py-2"><Badge variant="outline">{lead.status}</Badge></td>
                  <td className="py-2"><Badge variant="outline" className={
                    lead.rating === "hot" ? "bg-red-100 text-red-800" :
                    lead.rating === "warm" ? "bg-yellow-100 text-yellow-800" :
                    "bg-blue-100 text-blue-800"
                  }>{lead.rating}</Badge></td>
                  <td className="text-right py-2 font-medium">{lead.score}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
