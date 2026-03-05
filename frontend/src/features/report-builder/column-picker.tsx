import type { EntityFieldDef } from "./report-builder-types";

interface ColumnPickerProps {
  fields: EntityFieldDef[];
  selected: string[];
  onChange: (columns: string[]) => void;
}

export function ColumnPicker({ fields, selected, onChange }: ColumnPickerProps) {
  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onChange(selected.filter((c) => c !== name));
    } else {
      onChange([...selected, name]);
    }
  };

  return (
    <div>
      <label className="text-sm font-medium">Columns</label>
      <div className="mt-1 max-h-[200px] overflow-auto space-y-1">
        {fields.map((f) => (
          <label key={f.name} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-accent p-1 rounded">
            <input
              type="checkbox"
              checked={selected.includes(f.name)}
              onChange={() => toggle(f.name)}
              className="rounded"
            />
            {f.label}
          </label>
        ))}
      </div>
    </div>
  );
}
