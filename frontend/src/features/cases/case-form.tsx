import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CASE_PRIORITIES, CASE_ORIGINS } from "./cases-types";
import type { Case, CreateCaseRequest } from "./cases-types";

const caseSchema = z.object({
  subject: z.string().min(1, "Subject is required").max(500),
  description: z.string().min(1, "Description is required").max(10000),
  account_id: z.string().min(1, "Account ID is required"),
  case_number: z.string().min(1, "Case number is required").max(50),
  contact_id: z.string().optional().or(z.literal("")),
  priority: z.string().optional(),
  origin: z.string().optional(),
});

type CaseFormValues = z.infer<typeof caseSchema>;

interface CaseFormProps {
  defaultValues?: Case;
  ownerId: string;
  onSubmit: (data: CreateCaseRequest) => void;
  loading?: boolean;
}

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function CaseForm({ defaultValues, ownerId, onSubmit, loading }: CaseFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CaseFormValues>({
    resolver: zodResolver(caseSchema),
    defaultValues: defaultValues
      ? {
          subject: defaultValues.subject,
          description: defaultValues.description,
          account_id: defaultValues.account_id,
          case_number: defaultValues.case_number,
          contact_id: defaultValues.contact_id ?? "",
          priority: defaultValues.priority,
          origin: defaultValues.origin,
        }
      : { priority: "medium", origin: "web" },
  });

  const handleFormSubmit = (data: CaseFormValues) => {
    onSubmit({
      ...data,
      contact_id: data.contact_id || undefined,
      owner_id: ownerId,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="subject">Subject *</Label>
          <Input id="subject" {...register("subject")} />
          {errors.subject && <p className="text-sm text-destructive">{errors.subject.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="case_number">Case Number *</Label>
          <Input id="case_number" {...register("case_number")} />
          {errors.case_number && <p className="text-sm text-destructive">{errors.case_number.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="account_id">Account ID *</Label>
          <Input id="account_id" {...register("account_id")} />
          {errors.account_id && <p className="text-sm text-destructive">{errors.account_id.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="contact_id">Contact ID</Label>
          <Input id="contact_id" {...register("contact_id")} />
        </div>
        <div className="space-y-2">
          <Label>Priority</Label>
          <Select value={watch("priority") ?? "medium"} onValueChange={(v) => setValue("priority", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {CASE_PRIORITIES.map((p) => (
                <SelectItem key={p} value={p}>{formatLabel(p)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Origin</Label>
          <Select value={watch("origin") ?? "web"} onValueChange={(v) => setValue("origin", v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {CASE_ORIGINS.map((o) => (
                <SelectItem key={o} value={o}>{formatLabel(o)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description *</Label>
        <Textarea id="description" {...register("description")} rows={4} />
        {errors.description && <p className="text-sm text-destructive">{errors.description.message}</p>}
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Saving..." : defaultValues ? "Update Case" : "Create Case"}
      </Button>
    </form>
  );
}
