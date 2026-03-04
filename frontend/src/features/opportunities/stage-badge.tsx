import { Badge } from "@/components/ui/badge";

const stageColors: Record<string, string> = {
  prospecting: "bg-gray-100 text-gray-800",
  qualification: "bg-blue-100 text-blue-800",
  needs_analysis: "bg-indigo-100 text-indigo-800",
  value_proposition: "bg-purple-100 text-purple-800",
  decision_makers: "bg-yellow-100 text-yellow-800",
  proposal: "bg-orange-100 text-orange-800",
  negotiation: "bg-amber-100 text-amber-800",
  closed_won: "bg-green-100 text-green-800",
  closed_lost: "bg-red-100 text-red-800",
};

function formatLabel(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function StageBadge({ stage }: { stage: string }) {
  return (
    <Badge variant="outline" className={stageColors[stage] ?? ""}>
      {formatLabel(stage)}
    </Badge>
  );
}
