import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Contact, CreateContactRequest } from "./contacts-types";

const contactSchema = z.object({
  account_id: z.string().min(1, "Account ID is required"),
  first_name: z.string().min(1, "First name is required").max(100),
  last_name: z.string().min(1, "Last name is required").max(100),
  email: z.string().email("Invalid email"),
  phone: z.string().max(50).optional().or(z.literal("")),
  title: z.string().max(200).optional().or(z.literal("")),
  department: z.string().max(200).optional().or(z.literal("")),
});

type ContactFormValues = z.infer<typeof contactSchema>;

interface ContactFormProps {
  defaultValues?: Contact;
  ownerId: string;
  onSubmit: (data: CreateContactRequest) => void;
  loading?: boolean;
}

export function ContactForm({ defaultValues, ownerId, onSubmit, loading }: ContactFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: defaultValues
      ? {
          account_id: defaultValues.account_id,
          first_name: defaultValues.first_name,
          last_name: defaultValues.last_name,
          email: defaultValues.email,
          phone: defaultValues.phone ?? "",
          title: defaultValues.title ?? "",
          department: defaultValues.department ?? "",
        }
      : {},
  });

  const handleFormSubmit = (data: ContactFormValues) => {
    onSubmit({
      ...data,
      phone: data.phone || undefined,
      title: data.title || undefined,
      department: data.department || undefined,
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
          <Label htmlFor="account_id">Account ID *</Label>
          <Input id="account_id" {...register("account_id")} />
          {errors.account_id && <p className="text-sm text-destructive">{errors.account_id.message}</p>}
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
          <Label htmlFor="department">Department</Label>
          <Input id="department" {...register("department")} />
        </div>
      </div>
      <Button type="submit" disabled={loading}>
        {loading ? "Saving..." : defaultValues ? "Update Contact" : "Create Contact"}
      </Button>
    </form>
  );
}
