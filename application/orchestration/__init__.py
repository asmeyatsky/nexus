"""
DAG Orchestrator

Architectural Intent:
- Parallel-safe workflow orchestration
- Dependency graph for multi-step operations
- asyncio.gather for independent steps
"""

import asyncio
from typing import Dict, Any, Callable, Set, Optional
from dataclasses import dataclass, field


@dataclass
class DAGNode:
    name: str
    handler: Callable
    depends_on: Set[str] = field(default_factory=set)


class DAGOrchestrator:
    """Execute a directed acyclic graph of async tasks with maximum parallelism."""

    def __init__(self):
        self._nodes: Dict[str, DAGNode] = {}

    def add_node(
        self,
        name: str,
        handler: Callable,
        depends_on: Optional[Set[str]] = None,
    ):
        self._nodes[name] = DAGNode(
            name=name,
            handler=handler,
            depends_on=depends_on or set(),
        )

    async def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute all nodes respecting dependency order."""
        context = context or {}
        results: Dict[str, Any] = {}
        completed: Set[str] = set()
        pending = set(self._nodes.keys())

        failed: Set[str] = set()

        while pending:
            # Find nodes whose dependencies are all satisfied and none failed
            ready = [
                name
                for name in pending
                if self._nodes[name].depends_on.issubset(completed)
                and not self._nodes[name].depends_on.intersection(failed)
            ]

            # Skip nodes whose dependencies have failed
            blocked_by_failure = [
                name
                for name in pending
                if self._nodes[name].depends_on.intersection(failed)
            ]
            for name in blocked_by_failure:
                results[name] = {"error": "Skipped due to upstream failure"}
                failed.add(name)
                pending.discard(name)

            if not ready and pending:
                raise RuntimeError(f"Circular dependency detected. Pending: {pending}")

            if not ready:
                break

            # Execute ready nodes in parallel
            tasks = [self._execute_node(name, context, results) for name in ready]
            node_results = await asyncio.gather(*tasks, return_exceptions=True)

            for name, result in zip(ready, node_results):
                if isinstance(result, Exception):
                    results[name] = {"error": str(result)}
                    failed.add(name)
                else:
                    results[name] = result
                completed.add(name)
                pending.discard(name)

        return results

    async def _execute_node(
        self,
        name: str,
        context: Dict[str, Any],
        results: Dict[str, Any],
    ) -> Any:
        node = self._nodes[name]
        return await node.handler(context=context, results=results)

    def clear(self):
        self._nodes.clear()
