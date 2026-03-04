import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Lead, CreateLeadRequest } from "./leads-types";

const leadSchema = z.object({
  first_name: z.string().min(1, "First name is required").max(100),
  last_name: z.string().min(1, "Last name is required").max(100),
  email: z.string().email("Invalid email"),
  company: z.string().min(1, "Company is required").max(255),
  source: z.string().optional().or(z.literal("")),
  phone: z.string().max(50).optional().or(z.literal("")),
  title: z.string().max(200).optional().or(z.literal("")),
  website: z.string().max(2048).optional().or(z.literal("")),
});

type LeadFormValues = z.infer<typeof leadSchema>;

interface LeadFormProps {
  defaultValues?: Lead;
  ownerId: string;
  onSubmit: (data: CreateLeadRequest) => void;
  loading?: boolean;
}

export function LeadForm({ defaultValues, ownerId, onSubmit, loading }: LeadFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: defaultValues
      ? {
          first_name: defaultValues.first_name,
          last_name: defaultValues.last_name,
          email: defaultValues.email,
          company: defaultValues.company,
          source: defaultValues.source ?? "",
          phone: defaultValues.phone ?? "",
          title: defaultValues.title ?? "",
          website: defaultValues.website ?? "",
        }
      : {},
  });

  const handleFormSubmit = (data: LeadFormValues) => {
    onSubmit({
      ...data,
      source: data.source || undefined,
      phone: data.phone || undefined,
      title: data.title || undefined,
      website: data.website || undefined,
      owner_id: ownerId,
    });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name *</Label>
          <Input id="first_name" {...register("first_name")} />
          {errors.first_name && <p className="text-sm text-destructive">{errors.first_name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name *</Label>
          <Input id="last_name" {...register("last_name")} />
          {errors.last_name && <p className="text-sm text-destructive">{errors.last_name.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email *</Label>
          <Input id="email" type="email" {...register("email")} />
          {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="company">Company *</Label>
          <Input id="company" {...register("company")} />
          {errors.company && <p className="text-sm text-destructive">{errors.company.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone">Phone</Label>
          <Input id="phone" {...register("phone")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input id="title" {...register("title")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="source">Source</Label>
          <Input id="source" {...register("source")} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="website">Website</Label>
          <Input id="website" {...register("website")} placeholder="https://..." />
        </div>
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Saving..." : defaultValues ? "Update Lead" : "Create Lead"}
      </Button>
    </form>
  );
}
