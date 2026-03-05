import { Button } from "@/components/ui/button";
import { Table, BarChart3, PieChart, LineChart } from "lucide-react";
import { cn } from "@/lib/utils";

const CHART_TYPES = [
  { value: "table" as const, label: "Table", icon: Table },
  { value: "bar" as const, label: "Bar", icon: BarChart3 },
  { value: "pie" as const, label: "Pie", icon: PieChart },
  { value: "line" as const, label: "Line", icon: LineChart },
];

interface ChartTypePickerProps {
  value: "table" | "bar" | "pie" | "line";
  onChange: (value: "table" | "bar" | "pie" | "line") => void;
}

export function ChartTypePicker({ value, onChange }: ChartTypePickerProps) {
  return (
    <div>
      <label className="text-sm font-medium">Chart Type</label>
      <div className="mt-1 flex gap-1">
        {CHART_TYPES.map((ct) => (
          <Button
            key={ct.value}
            variant={value === ct.value ? "default" : "outline"}
            size="sm"
            className={cn("flex-1")}
            onClick={() => onChange(ct.value)}
          >
            <ct.icon className="mr-1 h-3 w-3" /> {ct.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
