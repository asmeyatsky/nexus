import apiClient from "@/lib/api-client";
import type { ReportConfig } from "./report-builder-types";

export const reportBuilderApi = {
  runQuery: (config: Omit<ReportConfig, "chart_type">) =>
    apiClient.post("/reports/query", config).then((r) => r.data),

  runCrossQuery: (config: {
    primary_entity: string;
    related_entity: string;
    related_filters: { field: string; operator: string; value: string }[];
    primary_columns?: string[];
    limit?: number;
  }) => apiClient.post("/reports/cross-query", config).then((r) => r.data),
};
