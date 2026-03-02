"""
DAG Orchestrator

Architectural Intent:
- Parallel-safe workflow orchestration
- Dependency graph for multi-step operations
- asyncio.gather for independent steps
"""

import asyncio
from typing import Dict, Any, Callable, List, Set, Optional
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

        while pending:
            # Find nodes whose dependencies are all satisfied
            ready = [
                name for name in pending
                if self._nodes[name].depends_on.issubset(completed)
            ]

            if not ready:
                raise RuntimeError(
                    f"Circular dependency detected. Pending: {pending}"
                )

            # Execute ready nodes in parallel
            tasks = [
                self._execute_node(name, context, results)
                for name in ready
            ]
            node_results = await asyncio.gather(*tasks, return_exceptions=True)

            for name, result in zip(ready, node_results):
                if isinstance(result, Exception):
                    results[name] = {"error": str(result)}
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
