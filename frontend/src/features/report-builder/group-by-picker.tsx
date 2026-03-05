import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { EntityFieldDef } from "./report-builder-types";

interface GroupByPickerProps {
  fields: EntityFieldDef[];
  value: string;
  onChange: (value: string) => void;
}

export function GroupByPicker({ fields, value, onChange }: GroupByPickerProps) {
  const groupableFields = fields.filter((f) => f.type === "string" || f.type === "boolean");

  return (
    <div>
      <label className="text-sm font-medium">Group By</label>
      <Select value={value || "none"} onValueChange={(v) => onChange(v === "none" ? "" : v)}>
        <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="none">None</SelectItem>
          {groupableFields.map((f) => (
            <SelectItem key={f.name} value={f.name}>{f.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
