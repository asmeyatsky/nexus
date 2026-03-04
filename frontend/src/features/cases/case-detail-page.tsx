import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { casesApi } from "./cases-api";
import { CASE_STATUSES } from "./cases-types";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ResolveCaseDialog } from "./resolve-case-dialog";
import { CaseForm } from "./case-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDelete, setShowDelete] = useState(false);
  const [showResolve, setShowResolve] = useState(false);
  const [showClose, setShowClose] = useState(false);
  const [newStatus, setNewStatus] = useState("");

  const { data: caseData, isLoading } = useQuery({
    queryKey: ["cases", id],
    queryFn: () => casesApi.get(id!),
  });

  const statusMutation = useMutation({
    mutationFn: (status: string) => casesApi.updateStatus(id!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      setNewStatus("");
      toast.success("Status updated");
    },
    onError: () => toast.error("Failed to update status"),
  });

  const resolveMutation = useMutation({
    mutationFn: (data: Parameters<typeof casesApi.resolve>[1]) => casesApi.resolve(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      setShowResolve(false);
      toast.success("Case resolved");
    },
    onError: () => toast.error("Failed to resolve case"),
  });

  const closeMutation = useMutation({
    mutationFn: () => casesApi.close(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      setShowClose(false);
      toast.success("Case closed");
    },
    onError: () => toast.error("Failed to close case"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => casesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cases"] });
      navigate("/cases");
      toast.success("Case deleted");
    },
  });

  if (isLoading || !caseData) return <LoadingSpinner />;

  const isClosed = caseData.status === "closed";
  const isResolved = caseData.status === "resolved";

  return (
    <div>
      <PageHeader
        title={`Case ${caseData.case_number}`}
        description={caseData.subject}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/cases")}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            {!isClosed && !isResolved && (
              <Button variant="outline" size="sm" onClick={() => setShowResolve(true)}>
                Resolve
              </Button>
            )}
            {!isClosed && (
              <Button variant="outline" size="sm" onClick={() => setShowClose(true)}>
                Close
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex gap-2">
        <Badge variant="outline">{formatLabel(caseData.status)}</Badge>
        <Badge variant="outline">{formatLabel(caseData.priority)}</Badge>
        <Badge variant="outline">{formatLabel(caseData.origin)}</Badge>
      </div>

      {!isClosed && (
        <Card className="mb-4">
          <CardHeader><CardTitle className="text-base">Change Status</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Select value={newStatus} onValueChange={setNewStatus}>
              <SelectTrigger className="w-56"><SelectValue placeholder="Select new status" /></SelectTrigger>
              <SelectContent>
                {CASE_STATUSES.filter((s) => s !== caseData.status).map((s) => (
                  <SelectItem key={s} value={s}>{formatLabel(s)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              disabled={!newStatus || statusMutation.isPending}
              onClick={() => statusMutation.mutate(newStatus)}
            >
              Update Status
            </Button>
          </CardContent>
        </Card>
      )}

      {caseData.resolution_notes && (
        <Card className="mb-4">
          <CardHeader><CardTitle className="text-base">Resolution</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm">{caseData.resolution_notes}</p>
            {caseData.resolved_at && (
              <p className="mt-2 text-xs text-muted-foreground">
                Resolved at {new Date(caseData.resolved_at).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Case Details</CardTitle></CardHeader>
        <CardContent>
          <CaseForm
            defaultValues={caseData}
            ownerId={user!.id}
            onSubmit={() => toast.info("Case updates are managed via status changes")}
          />
        </CardContent>
      </Card>

      <ResolveCaseDialog
        open={showResolve}
        onOpenChange={setShowResolve}
        onResolve={(data) => resolveMutation.mutate(data)}
        resolvedBy={user!.id}
        loading={resolveMutation.isPending}
      />

      <ConfirmDialog
        open={showClose}
        onOpenChange={setShowClose}
        title="Close Case"
        description="Are you sure you want to close this case?"
        confirmLabel="Close Case"
        onConfirm={() => closeMutation.mutate()}
        loading={closeMutation.isPending}
      />

      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Case"
        description="This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
