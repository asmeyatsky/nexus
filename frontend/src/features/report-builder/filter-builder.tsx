import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { OPERATORS, type EntityFieldDef, type FilterCondition } from "./report-builder-types";

interface FilterBuilderProps {
  fields: EntityFieldDef[];
  filters: FilterCondition[];
  onChange: (filters: FilterCondition[]) => void;
}

export function FilterBuilder({ fields, filters, onChange }: FilterBuilderProps) {
  const addFilter = () => {
    onChange([...filters, { field: fields[0]?.name ?? "", operator: "eq", value: "" }]);
  };

  const updateFilter = (index: number, updates: Partial<FilterCondition>) => {
    const updated = filters.map((f, i) => (i === index ? { ...f, ...updates } : f));
    onChange(updated);
  };

  const removeFilter = (index: number) => {
    onChange(filters.filter((_, i) => i !== index));
  };

  const fieldDef = (name: string) => fields.find((f) => f.name === name);

  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Filters</label>
        <Button variant="ghost" size="sm" onClick={addFilter}>
          <Plus className="mr-1 h-3 w-3" /> Add
        </Button>
      </div>
      <div className="mt-1 space-y-2">
        {filters.map((filter, i) => {
          const fd = fieldDef(filter.field);
          return (
            <div key={i} className="flex items-center gap-1">
              <Select value={filter.field} onValueChange={(v) => updateFilter(i, { field: v, value: "" })}>
                <SelectTrigger className="w-[110px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {fields.map((f) => <SelectItem key={f.name} value={f.name}>{f.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={filter.operator} onValueChange={(v) => updateFilter(i, { operator: v })}>
                <SelectTrigger className="w-[90px] h-8 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {OPERATORS.map((op) => <SelectItem key={op.value} value={op.value}>{op.label}</SelectItem>)}
                </SelectContent>
              </Select>
              {fd?.enumValues ? (
                <Select value={filter.value} onValueChange={(v) => updateFilter(i, { value: v })}>
                  <SelectTrigger className="flex-1 h-8 text-xs"><SelectValue placeholder="Value" /></SelectTrigger>
                  <SelectContent>
                    {fd.enumValues.map((ev) => <SelectItem key={ev.value} value={ev.value}>{ev.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  value={filter.value}
                  onChange={(e) => updateFilter(i, { value: e.target.value })}
                  placeholder="Value"
                  className="flex-1 h-8 text-xs"
                />
              )}
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={() => removeFilter(i)}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
