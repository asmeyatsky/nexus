import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PipelineReport } from "./pipeline-report";
import { LeadFunnelReport } from "./lead-funnel-report";
import { CaseMetricsReport } from "./case-metrics-report";
import { ActivityReport } from "./activity-report";

export function ReportsPage() {
  return (
    <div>
      <PageHeader title="Reports" description="Aggregated data and key metrics" />
      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
          <TabsTrigger value="leads">Lead Funnel</TabsTrigger>
          <TabsTrigger value="cases">Case Metrics</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>
        <TabsContent value="pipeline" className="mt-6"><PipelineReport /></TabsContent>
        <TabsContent value="leads" className="mt-6"><LeadFunnelReport /></TabsContent>
        <TabsContent value="cases" className="mt-6"><CaseMetricsReport /></TabsContent>
        <TabsContent value="activity" className="mt-6"><ActivityReport /></TabsContent>
      </Tabs>
    </div>
  );
}
