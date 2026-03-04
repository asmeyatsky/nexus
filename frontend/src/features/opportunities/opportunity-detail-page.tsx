import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { opportunitiesApi } from "./opportunities-api";
import { OPPORTUNITY_STAGES } from "./opportunities-types";
import { useAuth } from "@/features/auth/auth-context";
import { PageHeader } from "@/components/shared/page-header";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { OpportunityForm } from "./opportunity-form";
import { StageBadge } from "./stage-badge";
import { Button } from "@/components/ui/button";
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

export function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [showDelete, setShowDelete] = useState(false);
  const [newStage, setNewStage] = useState("");

  const { data: opp, isLoading } = useQuery({
    queryKey: ["opportunities", id],
    queryFn: () => opportunitiesApi.get(id!),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof opportunitiesApi.create>[0]) => opportunitiesApi.update(id!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities", id] });
      toast.success("Opportunity updated");
    },
    onError: () => toast.error("Failed to update opportunity"),
  });

  const stageMutation = useMutation({
    mutationFn: (stage: string) => opportunitiesApi.updateStage(id!, { stage }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
      setNewStage("");
      toast.success("Stage updated");
    },
    onError: () => toast.error("Failed to update stage"),
  });

  const deleteMutation = useMutation({
    mutationFn: () => opportunitiesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opportunities"] });
      navigate("/opportunities");
      toast.success("Opportunity deleted");
    },
  });

  if (isLoading || !opp) return <LoadingSpinner />;

  return (
    <div>
      <PageHeader
        title={opp.name}
        description={<StageBadge stage={opp.stage} /> as unknown as string}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate("/opportunities")}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
              Delete
            </Button>
          </div>
        }
      />

      {!opp.is_closed && (
        <Card className="mb-4">
          <CardHeader><CardTitle className="text-base">Change Stage</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Select value={newStage} onValueChange={setNewStage}>
              <SelectTrigger className="w-56"><SelectValue placeholder="Select new stage" /></SelectTrigger>
              <SelectContent>
                {OPPORTUNITY_STAGES.filter((s) => s !== opp.stage).map((s) => (
                  <SelectItem key={s} value={s}>{formatLabel(s)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              disabled={!newStage || stageMutation.isPending}
              onClick={() => stageMutation.mutate(newStage)}
            >
              Update Stage
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Opportunity Details</CardTitle></CardHeader>
        <CardContent>
          <OpportunityForm
            defaultValues={opp}
            ownerId={user!.id}
            onSubmit={(d) => updateMutation.mutate(d)}
            loading={updateMutation.isPending}
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        title="Delete Opportunity"
        description="This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
