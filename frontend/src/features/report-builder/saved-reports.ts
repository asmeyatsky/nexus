import type { ReportConfig } from "./report-builder-types";

const STORAGE_KEY = "nexus-saved-reports";

export interface SavedReport {
  name: string;
  config: ReportConfig;
  createdAt: string;
}

export function getSavedReports(): SavedReport[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function saveReport(name: string, config: ReportConfig): void {
  const reports = getSavedReports().filter((r) => r.name !== name);
  reports.push({ name, config, createdAt: new Date().toISOString() });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(reports));
}

export function deleteSavedReport(name: string): void {
  const reports = getSavedReports().filter((r) => r.name !== name);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(reports));
}
