import { useState, useMemo } from "react";
import { useDebounce } from "./use-debounce";

export interface FilterState {
  search: string;
  [key: string]: string;
}

export function useFilters(initialFilters: Record<string, string> = {}) {
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    ...initialFilters,
  });
  const [page, setPage] = useState(1);
  const limit = 20;

  const debouncedSearch = useDebounce(filters.search, 300);

  const setFilter = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    const cleared: FilterState = { search: "" };
    for (const key of Object.keys(filters)) {
      cleared[key] = "";
    }
    setFilters(cleared);
    setPage(1);
  };

  const queryParams = useMemo(() => {
    const params: Record<string, string | number> = {
      limit,
      offset: (page - 1) * limit,
    };
    if (debouncedSearch) params.search = debouncedSearch;
    for (const [key, value] of Object.entries(filters)) {
      if (key !== "search" && value) {
        params[key] = value;
      }
    }
    return params;
  }, [debouncedSearch, filters, page]);

  const hasActiveFilters = useMemo(
    () => Object.values(filters).some((v) => v !== ""),
    [filters]
  );

  return {
    filters,
    setFilter,
    clearFilters,
    queryParams,
    hasActiveFilters,
    page,
    setPage,
    limit,
  };
}
