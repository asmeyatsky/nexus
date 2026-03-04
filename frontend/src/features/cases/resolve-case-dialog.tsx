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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface ResolveCaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onResolve: (data: { resolution_notes: string; resolved_by: string }) => void;
  resolvedBy: string;
  loading?: boolean;
}

export function ResolveCaseDialog({ open, onOpenChange, onResolve, resolvedBy, loading }: ResolveCaseDialogProps) {
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onResolve({ resolution_notes: notes, resolved_by: resolvedBy });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Resolve Case</DialogTitle>
          <DialogDescription>Provide resolution notes to close this case.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="resolution_notes">Resolution Notes *</Label>
            <Textarea
              id="resolution_notes"
              required
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !notes.trim()}>
              {loading ? "Resolving..." : "Resolve"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
