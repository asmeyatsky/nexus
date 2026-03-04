import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ConvertLeadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConvert: (data: { account_id: string; contact_id: string; opportunity_id?: string }) => void;
  loading?: boolean;
}

export function ConvertLeadDialog({ open, onOpenChange, onConvert, loading }: ConvertLeadDialogProps) {
  const [accountId, setAccountId] = useState("");
  const [contactId, setContactId] = useState("");
  const [opportunityId, setOpportunityId] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConvert({
      account_id: accountId,
      contact_id: contactId,
      opportunity_id: opportunityId || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Convert Lead</DialogTitle>
          <DialogDescription>
            Link this lead to an existing account and contact to convert it.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="conv-account">Account ID *</Label>
            <Input id="conv-account" required value={accountId} onChange={(e) => setAccountId(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="conv-contact">Contact ID *</Label>
            <Input id="conv-contact" required value={contactId} onChange={(e) => setContactId(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="conv-opp">Opportunity ID (optional)</Label>
            <Input id="conv-opp" value={opportunityId} onChange={(e) => setOpportunityId(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !accountId || !contactId}>
              {loading ? "Converting..." : "Convert"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
