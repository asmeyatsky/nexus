import { useQuery } from "@tanstack/react-query";
import { Building2, TrendingUp, Headphones, UserPlus } from "lucide-react";
import apiClient from "@/lib/api-client";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "./stat-card";
import { LoadingSpinner } from "@/components/shared/loading-spinner";

export function DashboardPage() {
  const accounts = useQuery({
    queryKey: ["accounts", { limit: 1, offset: 0 }],
    queryFn: () => apiClient.get("/accounts", { params: { limit: 100 } }).then((r) => r.data),
  });
  const openOpps = useQuery({
    queryKey: ["opportunities-open"],
    queryFn: () => apiClient.get("/opportunities/open", { params: { limit: 100 } }).then((r) => r.data),
  });
  const openCases = useQuery({
    queryKey: ["cases-open"],
    queryFn: () => apiClient.get("/cases/open", { params: { limit: 100 } }).then((r) => r.data),
  });
  const leads = useQuery({
    queryKey: ["leads", { limit: 1, offset: 0 }],
    queryFn: () => apiClient.get("/leads", { params: { limit: 100 } }).then((r) => r.data),
  });

  const isLoading = accounts.isLoading || openOpps.isLoading || openCases.isLoading || leads.isLoading;

  if (isLoading) return <LoadingSpinner />;

  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of your CRM" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Accounts" value={accounts.data?.length ?? 0} icon={Building2} />
        <StatCard title="Open Opportunities" value={openOpps.data?.length ?? 0} icon={TrendingUp} />
        <StatCard title="Open Cases" value={openCases.data?.length ?? 0} icon={Headphones} />
        <StatCard title="Active Leads" value={leads.data?.length ?? 0} icon={UserPlus} />
      </div>
    </div>
  );
}
