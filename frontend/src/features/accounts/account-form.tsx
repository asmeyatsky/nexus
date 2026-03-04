import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { INDUSTRIES, TERRITORIES, type CreateAccountRequest } from "./accounts-types";
import type { Account } from "./accounts-types";

const accountSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  industry: z.string().min(1, "Industry is required"),
  territory: z.string().min(1, "Territory is required"),
  website: z.string().max(2048).optional().or(z.literal("")),
  phone: z.string().max(50).optional().or(z.literal("")),
  billing_address: z.string().max(500).optional().or(z.literal("")),
  annual_revenue: z.string().optional().or(z.literal("")),
  currency: z.string().max(10).optional(),
  employee_count: z.string().optional().or(z.literal("")),
});

type AccountFormValues = z.infer<typeof accountSchema>;

interface AccountFormProps {
  defaultValues?: Account;
  ownerId: string;
  onSubmit: (data: CreateAccountRequest) => void;
  loading?: boolean;
}

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function AccountForm({ defaultValues, ownerId, onSubmit, loading }: AccountFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AccountFormValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: defaultValues
      ? {
          name: defaultValues.name,
          industry: defaultValues.industry,
          territory: defaultValues.territory,
          website: defaultValues.website ?? "",
          phone: defaultValues.phone ?? "",
          billing_address: defaultValues.billing_address ?? "",
          annual_revenue: defaultValues.annual_revenue?.toString() ?? "",
          currency: defaultValues.currency ?? "USD",
          employee_count: defaultValues.employee_count?.toString() ?? "",
        }
      : { currency: "USD" },
  });

  const handleFormSubmit = (data: AccountFormValues) => {
    onSubmit({
      name: data.name,
      industry: data.industry,
      territory: data.territory,
      owner_id: ownerId,
      website: data.website || undefined,
      phone: data.phone || undefined,
      billing_address: data.billing_address || undefined,
      annual_revenue: data.annual_revenue ? parseFloat(data.annual_revenue) : undefined,
      currency: data.currency || "USD",
      employee_count: data.employee_count ? parseInt(data.employee_count) : undefined,
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
          <Label>Industry *</Label>
          <Select value={watch("industry") ?? ""} onValueChange={(v) => setValue("industry", v)}>
            <SelectTrigger><SelectValue placeholder="Select industry" /></SelectTrigger>
            <SelectContent>
              {INDUSTRIES.map((i) => (
                <SelectItem key={i} value={i}>{formatLabel(i)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.industry && <p className="text-sm text-destructive">{errors.industry.message}</p>}
        </div>

        <div className="space-y-2">
          <Label>Territory *</Label>
          <Select value={watch("territory") ?? ""} onValueChange={(v) => setValue("territory", v)}>
            <SelectTrigger><SelectValue placeholder="Select territory" /></SelectTrigger>
            <SelectContent>
              {TERRITORIES.map((t) => (
                <SelectItem key={t} value={t}>{formatLabel(t)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.territory && <p className="text-sm text-destructive">{errors.territory.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="website">Website</Label>
          <Input id="website" {...register("website")} placeholder="https://..." />
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone">Phone</Label>
          <Input id="phone" {...register("phone")} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="billing_address">Billing Address</Label>
          <Input id="billing_address" {...register("billing_address")} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="annual_revenue">Annual Revenue</Label>
          <Input id="annual_revenue" type="number" step="0.01" {...register("annual_revenue")} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="employee_count">Employee Count</Label>
          <Input id="employee_count" type="number" {...register("employee_count")} />
        </div>
      </div>

      <Button type="submit" disabled={loading}>
        {loading ? "Saving..." : defaultValues ? "Update Account" : "Create Account"}
      </Button>
    </form>
  );
}
