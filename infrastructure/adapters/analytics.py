"""
BigQuery Analytics & Reporting

Architectural Intent:
- Data warehouse integration with BigQuery
- Real-time analytics
- Custom report builder
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json


class ReportType(Enum):
    SALES_PIPELINE = "sales_pipeline"
    FORECAST = "forecast"
    ACTIVITY = "activity"
    CONVERSION = "conversion"
    CUSTOM = "custom"


@dataclass
class ReportDefinition:
    id: str
    name: str
    report_type: ReportType
    dimensions: List[str]
    metrics: List[str]
    filters: Dict[str, Any]
    group_by: List[str]
    org_id: str


class BigQueryReporter:
    """BigQuery analytics integration."""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self._client = None
        self._datasets = {}
    
    async def initialize(self):
        """Initialize BigQuery client."""
        if not self.project_id:
            print("BigQuery: Running in mock mode")
            return
        
        try:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project_id)
            self._datasets = {
                "events": "nexus_analytics.events",
                "pipeline": "nexus_analytics.pipeline",
                "activity": "nexus_analytics.activity",
            }
        except Exception as e:
            print(f"BigQuery initialization error: {e}")
    
    async def export_events(self, events: List[Dict]):
        """Export events to BigQuery."""
        if not self._client:
            print(f"BigQuery mock: Exporting {len(events)} events")
            return
        
        table = f"{self.project_id}.nexus_analytics.events"
        errors = self._client.insert_rows_json(table, events)
        
        if errors:
            print(f"BigQuery insert errors: {errors}")
    
    async def run_query(self, query: str) -> List[Dict]:
        """Execute a query."""
        if not self._client:
            return []
        
        query_job = self._client.query(query)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    async def get_pipeline_summary(
        self,
        org_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """Get sales pipeline summary = f."""
        
        query"""
        SELECT 
            stage,
            COUNT(*) as count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}'
            AND created_at BETWEEN @start_date AND @end_date
        GROUP BY stage
        """
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        
        results = await self.run_query(query)
        
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "by_stage": results,
        }
    
    async def get_forecast(
        self,
        org_id: str,
        quarters: int = 4,
    ) -> Dict:
        """Get sales forecast."""
        
        query = f"""
        SELECT 
            DATE_TRUNC(close_date, QUARTER) as quarter,
            SUM(amount) as pipeline,
            COUNT(*) as opportunities
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}'
            AND close_date >= CURRENT_DATE()
            AND stage NOT IN ('closed_won', 'closed_lost')
        GROUP BY quarter
        ORDER BY quarter
        LIMIT @quarters
        """
        
        results = await self.run_query(query)
        
        total_pipeline = sum(r.get("pipeline", 0) for r in results)
        
        return {
            "forecast": results,
            "total_pipeline": total_pipeline,
            "weighted_value": total_pipeline * 0.4,
        }
    
    async def get_activity_report(
        self,
        org_id: str,
        user_id: str = None,
        days: int = 30,
    ) -> Dict:
        """Get user activity report."""
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = f"""
        SELECT 
            user_id,
            activity_type,
            COUNT(*) as count,
            COUNT(DISTINCT record_id) as unique_records
        FROM `{self.project_id}.nexus_analytics.activity`
        WHERE org_id = '{org_id}'
            AND created_at >= @start_date
        """
        
        if user_id:
            query += f" AND user_id = '{user_id}'"
        
        query += " GROUP BY user_id, activity_type ORDER BY count DESC"
        
        results = await self.run_query(query)
        
        return {
            "period_days": days,
            "activities": results,
        }
    
    async def get_conversion_funnel(
        self,
        org_id: str,
    ) -> Dict:
        """Get conversion funnel analytics."""
        
        query = f"""
        SELECT 
            'leads' as stage,
            COUNT(*) as count
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}'
        UNION ALL
        SELECT 
            'qualified' as stage,
            COUNT(*) as count
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}' AND status = 'qualified'
        UNION ALL
        SELECT 
            'opportunities' as stage,
            COUNT(*) as count
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}' AND type = 'opportunity'
        UNION ALL
        SELECT 
            'won' as stage,
            COUNT(*) as count
        FROM `{self.project_id}.nexus_analytics.pipeline`
        WHERE org_id = '{org_id}' AND stage = 'closed_won'
        """
        
        results = await self.run_query(query)
        
        return {"funnel": results}
    
    def create_report(
        self,
        name: str,
        report_type: ReportType,
        dimensions: List[str],
        metrics: List[str],
        org_id: str,
        filters: Dict[str, Any] = None,
    ) -> ReportDefinition:
        """Create a custom report definition."""
        
        report = ReportDefinition(
            id=str(uuid4()),
            name=name,
            report_type=report_type,
            dimensions=dimensions,
            metrics=metrics,
            filters=filters or {},
            group_by=dimensions[:2] if dimensions else [],
            org_id=org_id,
        )
        
        return report
    
    async def generate_report(self, report: ReportDefinition) -> Dict:
        """Generate report from definition."""
        
        dimensions_str = ", ".join(report.dimensions)
        metrics_str = ", ".join([f"SUM({m}) as {m}" for m in report.metrics])
        
        query = f"""
        SELECT 
            {dimensions_str},
            {metrics_str}
        FROM `{self.project_id}.nexus_analytics.events`
        WHERE org_id = '{report.org_id}'
        """
        
        if report.group_by:
            query += f" GROUP BY {', '.join(report.group_by)}"
        
        results = await self.run_query(query)
        
        return {
            "report_id": report.id,
            "report_name": report.name,
            "data": results,
        }


from uuid import uuid4

bigquery_reporter = BigQueryReporter()
