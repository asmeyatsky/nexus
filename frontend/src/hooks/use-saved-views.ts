import { useState, useEffect } from "react";
import type { FilterState } from "./use-filters";

interface SavedView {
  name: string;
  filters: FilterState;
}

export function useSavedViews(entity: string) {
  const storageKey = `nexus-views-${entity}`;
  const [views, setViews] = useState<SavedView[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) setViews(JSON.parse(stored));
    } catch {
      // ignore
    }
  }, [storageKey]);

  const saveView = (name: string, filters: FilterState) => {
    const updated = [...views.filter((v) => v.name !== name), { name, filters }];
    setViews(updated);
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };

  const deleteView = (name: string) => {
    const updated = views.filter((v) => v.name !== name);
    setViews(updated);
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };

  return { views, saveView, deleteView };
}
