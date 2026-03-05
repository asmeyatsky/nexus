import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import type { SavedReport } from "./saved-reports";
import type { ReportConfig } from "./report-builder-types";

interface SavedReportsListProps {
  reports: SavedReport[];
  onLoad: (config: ReportConfig) => void;
  onDelete: (name: string) => void;
}

export function SavedReportsList({ reports, onLoad, onDelete }: SavedReportsListProps) {
  if (reports.length === 0) {
    return <p className="text-xs text-muted-foreground py-2">No saved reports</p>;
  }

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">Saved Reports</label>
      {reports.map((r) => (
        <div
          key={r.name}
          className="flex items-center justify-between p-2 rounded hover:bg-accent cursor-pointer text-sm"
          onClick={() => onLoad(r.config)}
        >
          <span className="truncate">{r.name}</span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 shrink-0"
            onClick={(e) => { e.stopPropagation(); onDelete(r.name); }}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      ))}
    </div>
  );
}
