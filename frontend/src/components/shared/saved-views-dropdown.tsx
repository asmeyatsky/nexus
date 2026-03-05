import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bookmark, Trash2 } from "lucide-react";
import type { FilterState } from "@/hooks/use-filters";

interface SavedViewsDropdownProps {
  views: { name: string; filters: FilterState }[];
  onLoad: (filters: FilterState) => void;
  onSave: (name: string) => void;
  onDelete: (name: string) => void;
}

export function SavedViewsDropdown({
  views,
  onLoad,
  onSave,
  onDelete,
}: SavedViewsDropdownProps) {
  const [saveName, setSaveName] = useState("");
  const [showSave, setShowSave] = useState(false);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Bookmark className="mr-1 h-4 w-4" /> Views
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {views.map((v) => (
          <DropdownMenuItem
            key={v.name}
            className="flex items-center justify-between"
            onSelect={() => onLoad(v.filters)}
          >
            <span>{v.name}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(v.name);
              }}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </DropdownMenuItem>
        ))}
        {views.length > 0 && <DropdownMenuSeparator />}
        {showSave ? (
          <div className="flex gap-1 p-2">
            <Input
              placeholder="View name"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              className="h-8 text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter" && saveName.trim()) {
                  onSave(saveName.trim());
                  setSaveName("");
                  setShowSave(false);
                }
              }}
            />
            <Button
              size="sm"
              className="h-8"
              onClick={() => {
                if (saveName.trim()) {
                  onSave(saveName.trim());
                  setSaveName("");
                  setShowSave(false);
                }
              }}
            >
              Save
            </Button>
          </div>
        ) : (
          <DropdownMenuItem onSelect={() => setShowSave(true)}>
            Save current view...
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
