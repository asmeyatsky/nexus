"""Forecasting Service — revenue forecasting based on pipeline data."""

from typing import List, Dict
from domain.entities import Opportunity


class ForecastingService:
    """Revenue forecasting based on pipeline data."""

    def calculate_weighted_pipeline(self, opportunities: List[Opportunity]) -> float:
        return sum(opp.weighted_value for opp in opportunities if not opp.is_closed)

    def forecast_by_stage(
        self, opportunities: List[Opportunity]
    ) -> Dict[str, Dict[str, float]]:
        stages: Dict[str, Dict[str, float]] = {}
        for opp in opportunities:
            if opp.is_closed:
                continue
            stage = opp.stage.value if hasattr(opp.stage, "value") else str(opp.stage)
            if stage not in stages:
                stages[stage] = {"count": 0, "total": 0.0, "weighted": 0.0}
            stages[stage]["count"] += 1
            stages[stage]["total"] += opp.amount
            stages[stage]["weighted"] += opp.weighted_value
        return stages
