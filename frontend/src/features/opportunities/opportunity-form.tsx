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
import { OPPORTUNITY_SOURCES, type CreateOpportunityRequest } from "./opportunities-types";
import type { Opportunity } from "./opportunities-types";

const oppSchema = z.object({
  account_id: z.string().min(1, "Account ID is required"),
  name: z.string().min(1, "Name is required").max(255),
  amount: z.string().min(1, "Amount is required"),
  currency: z.string().min(1).max(10),
  close_date: z.string().min(1, "Close date is required"),
  source: z.string().optional().or(z.literal("")),
  contact_id: z.string().optional().or(z.literal("")),
  description: z.string().max(5000).optional().or(z.literal("")),
});

type OppFormValues = z.infer<typeof oppSchema>;

interface OppFormProps {
  defaultValues?: Opportunity;
  ownerId: string;
  onSubmit: (data: CreateOpportunityRequest) => void;
  loading?: boolean;
}

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function OpportunityForm({ defaultValues, ownerId, onSubmit, loading }: OppFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<OppFormValues>({
    resolver: zodResolver(oppSchema),
    defaultValues: defaultValues
      ? {
          account_id: defaultValues.account_id,
          name: defaultValues.name,
          amount: defaultValues.amount.toString(),
          currency: defaultValues.currency,
          close_date: defaultValues.close_date.split("T")[0],
          source: defaultValues.source ?? "",
          contact_id: defaultValues.contact_id ?? "",
          description: defaultValues.description ?? "",
        }
      : { currency: "USD" },
  });

  const handleFormSubmit = (data: OppFormValues) => {
    onSubmit({
      account_id: data.account_id,
      name: data.name,
      amount: parseFloat(data.amount),
      currency: data.currency,
      close_date: data.close_date,
      owner_id: ownerId,
      source: data.source || undefined,
      contact_id: data.contact_id || undefined,
      description: data.description || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">Name *</Label>
          <Input id="name" {...register("name")} />
          {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="account_id">Account ID *</Label>
          <Input id="account_id" {...register("account_id")} />
          {errors.account_id && <p className="text-sm text-destructive">{errors.account_id.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="amount">Amount *</Label>
          <Input id="amount" type="number" step="0.01" {...register("amount")} />
          {errors.amount && <p className="text-sm text-destructive">{errors.amount.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="currency">Currency</Label>
          <Input id="currency" {...register("currency")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="close_date">Close Date *</Label>
          <Input id="close_date" type="date" {...register("close_date")} />
          {errors.close_date && <p className="text-sm text-destructive">{errors.close_date.message}</p>}
        </div>
        <div className="space-y-2">
          <Label>Source</Label>
          <Select value={watch("source") ?? ""} onValueChange={(v) => setValue("source", v)}>
            <SelectTrigger><SelectValue placeholder="Select source" /></SelectTrigger>
            <SelectContent>
              {OPPORTUNITY_SOURCES.map((s) => (
                <SelectItem key={s} value={s}>{formatLabel(s)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="contact_id">Contact ID</Label>
          <Input id="contact_id" {...register("contact_id")} />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" {...register("description")} rows={3} />
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Saving..." : defaultValues ? "Update Opportunity" : "Create Opportunity"}
      </Button>
    </form>
  );
}
