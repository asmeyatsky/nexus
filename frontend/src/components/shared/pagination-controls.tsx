import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationControlsProps {
  page: number;
  hasMore: boolean;
  onPrev: () => void;
  onNext: () => void;
  total?: number;
  limit?: number;
}

export function PaginationControls({ page, hasMore, onPrev, onNext, total, limit }: PaginationControlsProps) {
  const start = total != null && total > 0 ? (page - 1) * (limit ?? 20) + 1 : 0;
  const end = total != null ? Math.min(page * (limit ?? 20), total) : 0;

  return (
    <div className="flex items-center justify-between pt-4">
      <span className="text-sm text-muted-foreground">
        {total != null ? `Showing ${start}-${end} of ${total} results` : `Page ${page}`}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" onClick={onPrev} disabled={page <= 1}>
          <ChevronLeft className="mr-1 h-4 w-4" /> Previous
        </Button>
        <Button variant="outline" size="sm" onClick={onNext} disabled={!hasMore}>
          Next <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
