import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Play, Save } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { reportBuilderApi } from "./report-builder-api";
import { EntityPicker } from "./entity-picker";
import { ColumnPicker } from "./column-picker";
import { FilterBuilder } from "./filter-builder";
import { ChartTypePicker } from "./chart-type-picker";
import { GroupByPicker } from "./group-by-picker";
import { ReportResults } from "./report-results";
import { SavedReportsList } from "./saved-reports-list";
import { getSavedReports, saveReport, deleteSavedReport } from "./saved-reports";
import { ENTITY_FIELDS, type ReportConfig, type FilterCondition } from "./report-builder-types";

export function ReportBuilderPage() {
  const [entity, setEntity] = useState("accounts");
  const [columns, setColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterCondition[]>([]);
  const [sortBy, setSortBy] = useState("");
  const [sortOrder, setSortOrder] = useState("asc");
  const [groupBy, setGroupBy] = useState("");
  const [chartType, setChartType] = useState<"table" | "bar" | "pie" | "line">("table");
  const [limit, setLimit] = useState(100);
  const [saveName, setSaveName] = useState("");
  const [savedReports, setSavedReports] = useState(getSavedReports);
  const [results, setResults] = useState<unknown>(null);

  const fields = ENTITY_FIELDS[entity] ?? [];

  const runMutation = useMutation({
    mutationFn: () =>
      reportBuilderApi.runQuery({
        entity,
        columns: columns.length > 0 ? columns : undefined,
        filters: filters.length > 0 ? filters : undefined,
        sort_by: sortBy || undefined,
        sort_order: sortOrder,
        group_by: groupBy || undefined,
        limit,
      }),
    onSuccess: (data) => {
      setResults(data);
    },
    onError: () => toast.error("Query failed"),
  });

  const handleSave = () => {
    if (!saveName.trim()) return;
    const config: ReportConfig = {
      entity,
      columns: columns.length > 0 ? columns : undefined,
      filters: filters.length > 0 ? filters : undefined,
      sort_by: sortBy || undefined,
      sort_order: sortOrder,
      group_by: groupBy || undefined,
      limit,
      chart_type: chartType,
    };
    saveReport(saveName.trim(), config);
    setSavedReports(getSavedReports());
    setSaveName("");
    toast.success("Report saved");
  };

  const handleLoadConfig = (config: ReportConfig) => {
    setEntity(config.entity);
    setColumns(config.columns ?? []);
    setFilters(config.filters ?? []);
    setSortBy(config.sort_by ?? "");
    setSortOrder(config.sort_order);
    setGroupBy(config.group_by ?? "");
    setChartType(config.chart_type);
    setLimit(config.limit);
    setResults(null);
  };

  const handleDeleteReport = (name: string) => {
    deleteSavedReport(name);
    setSavedReports(getSavedReports());
  };

  const handleEntityChange = (e: string) => {
    setEntity(e);
    setColumns([]);
    setFilters([]);
    setSortBy("");
    setGroupBy("");
    setResults(null);
  };

  return (
    <div>
      <PageHeader title="Report Builder" description="Create custom reports with filters and charts" />
      <div className="flex gap-6">
        <Card className="w-1/3 shrink-0">
          <CardContent className="p-4 space-y-4">
            <EntityPicker value={entity} onChange={handleEntityChange} />
            <Separator />
            <ColumnPicker fields={fields} selected={columns} onChange={setColumns} />
            <Separator />
            <FilterBuilder fields={fields} filters={filters} onChange={setFilters} />
            <Separator />
            <GroupByPicker fields={fields} value={groupBy} onChange={setGroupBy} />
            <Separator />
            <ChartTypePicker value={chartType} onChange={setChartType} />
            <Separator />
            <div className="flex gap-2">
              <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending} className="flex-1">
                <Play className="mr-1 h-4 w-4" /> Run
              </Button>
            </div>
            <div className="flex gap-1">
              <Input
                placeholder="Report name"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                className="h-8 text-sm"
              />
              <Button variant="outline" size="sm" onClick={handleSave} disabled={!saveName.trim()}>
                <Save className="mr-1 h-3 w-3" /> Save
              </Button>
            </div>
            <Separator />
            <SavedReportsList reports={savedReports} onLoad={handleLoadConfig} onDelete={handleDeleteReport} />
          </CardContent>
        </Card>

        <div className="flex-1 min-w-0">
          {results ? (
            <ReportResults data={results} chartType={chartType} groupBy={groupBy} />
          ) : (
            <Card>
              <CardContent className="py-16 text-center text-muted-foreground">
                Configure your report and click Run to see results
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
