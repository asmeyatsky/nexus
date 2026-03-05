import { PageHeader } from "@/components/shared/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RevenueForecastPanel } from "./revenue-forecast-panel";
import { LeadScoringPanel } from "./lead-scoring-panel";
import { TrendsPanel } from "./trends-panel";
import { WinLossPanel } from "./win-loss-panel";

export function AnalyticsPage() {
  return (
    <div>
      <PageHeader title="Analytics" description="Advanced analytics and forecasting" />
      <Tabs defaultValue="forecast">
        <TabsList>
          <TabsTrigger value="forecast">Revenue Forecast</TabsTrigger>
          <TabsTrigger value="scoring">Lead Scoring</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="winloss">Win/Loss</TabsTrigger>
        </TabsList>
        <TabsContent value="forecast" className="mt-6"><RevenueForecastPanel /></TabsContent>
        <TabsContent value="scoring" className="mt-6"><LeadScoringPanel /></TabsContent>
        <TabsContent value="trends" className="mt-6"><TrendsPanel /></TabsContent>
        <TabsContent value="winloss" className="mt-6"><WinLossPanel /></TabsContent>
      </Tabs>
    </div>
  );
}
