import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ENTITIES = [
  { value: "accounts", label: "Accounts" },
  { value: "contacts", label: "Contacts" },
  { value: "opportunities", label: "Opportunities" },
  { value: "leads", label: "Leads" },
  { value: "cases", label: "Cases" },
];

interface EntityPickerProps {
  value: string;
  onChange: (value: string) => void;
}

export function EntityPicker({ value, onChange }: EntityPickerProps) {
  return (
    <div>
      <label className="text-sm font-medium">Entity</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger><SelectValue placeholder="Select entity" /></SelectTrigger>
        <SelectContent>
          {ENTITIES.map((e) => <SelectItem key={e.value} value={e.value}>{e.label}</SelectItem>)}
        </SelectContent>
      </Select>
    </div>
  );
}
