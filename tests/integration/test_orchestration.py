"""
DAG Orchestration Tests

Tests for parallel workflow orchestration.
"""

import pytest
import asyncio
from application.orchestration import DAGOrchestrator


@pytest.mark.asyncio
async def test_simple_dag():
    dag = DAGOrchestrator()

    async def step_a(context, results):
        return "result_a"

    async def step_b(context, results):
        return "result_b"

    async def step_c(context, results):
        return f"{results.get('step_a', '')}+{results.get('step_b', '')}"

    dag.add_node("step_a", step_a)
    dag.add_node("step_b", step_b)
    dag.add_node("step_c", step_c, depends_on={"step_a", "step_b"})

    results = await dag.execute()
    assert results["step_a"] == "result_a"
    assert results["step_b"] == "result_b"
    assert results["step_c"] == "result_a+result_b"


@pytest.mark.asyncio
async def test_parallel_execution():
    """Verify independent nodes run in parallel."""
    dag = DAGOrchestrator()
    execution_order = []

    async def node(name, delay):
        async def handler(context, results):
            execution_order.append(f"{name}_start")
            await asyncio.sleep(delay)
            execution_order.append(f"{name}_end")
            return name
        return handler

    dag.add_node("fast", await node("fast", 0.01))
    dag.add_node("slow", await node("slow", 0.05))

    results = await dag.execute()
    assert results["fast"] == "fast"
    assert results["slow"] == "slow"
    # Both should start before either finishes (parallel)
    assert execution_order[0] in ("fast_start", "slow_start")
    assert execution_order[1] in ("fast_start", "slow_start")


@pytest.mark.asyncio
async def test_error_handling():
    dag = DAGOrchestrator()

    async def failing_step(context, results):
        raise ValueError("intentional failure")

    dag.add_node("fail", failing_step)
    results = await dag.execute()
    assert "error" in results["fail"]


@pytest.mark.asyncio
async def test_circular_dependency_detection():
    dag = DAGOrchestrator()

    async def noop(context, results):
        return "ok"

    dag.add_node("a", noop, depends_on={"b"})
    dag.add_node("b", noop, depends_on={"a"})

    with pytest.raises(RuntimeError, match="Circular dependency"):
        await dag.execute()
