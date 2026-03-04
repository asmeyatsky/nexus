import { useState, useCallback } from "react";

export function usePagination(pageSize = 20) {
  const [offset, setOffset] = useState(0);

  const nextPage = useCallback(() => setOffset((o) => o + pageSize), [pageSize]);
  const prevPage = useCallback(() => setOffset((o) => Math.max(0, o - pageSize)), [pageSize]);
  const resetPage = useCallback(() => setOffset(0), []);

  return {
    limit: pageSize,
    offset,
    page: Math.floor(offset / pageSize) + 1,
    nextPage,
    prevPage,
    resetPage,
  };
}
