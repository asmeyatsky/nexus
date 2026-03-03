"""Tests for the Salesforce data migration tool."""

import json
import os
import tempfile

import pytest
from uuid import uuid4, UUID

from infrastructure.adapters.salesforce_migration import (
    IDRemapper,
    SalesforceObjectMapper,
    SalesforceDataSource,
    SalesforceMigrator,
    MigrationConfig,
    MigrationPhase,
    _normalise_stage,
    _normalise_lead_status,
    _normalise_case_priority,
    _infer_territory_region,
    _normalise_case_origin,
    _parse_amount,
)


# ---------------------------------------------------------------------------
# IDRemapper
# ---------------------------------------------------------------------------


class TestIDRemapper:
    def setup_method(self):
        self.mapper = IDRemapper()

    def test_register_and_get(self):
        nid = self.mapper.register("Account", "SF001")
        assert isinstance(nid, UUID)
        assert self.mapper.get("Account", "SF001") == nid

    def test_idempotent_registration(self):
        id1 = self.mapper.register("Account", "SF001")
        id2 = self.mapper.register("Account", "SF001")
        assert id1 == id2

    def test_missing_id_returns_none(self):
        assert self.mapper.get("Account", "NONEXISTENT") is None

    def test_count(self):
        self.mapper.register("Account", "SF001")
        self.mapper.register("Account", "SF002")
        self.mapper.register("Contact", "SFC001")
        assert self.mapper.count("Account") == 2
        assert self.mapper.count() == 3

    def test_save_and_load(self):
        self.mapper.register("Account", "SF001")
        self.mapper.register("Contact", "SFC001")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            self.mapper.save_to_file(path)
            new_mapper = IDRemapper()
            new_mapper.load_from_file(path)
            assert new_mapper.get("Account", "SF001") == self.mapper.get(
                "Account", "SF001"
            )
            assert new_mapper.count() == 2
        finally:
            os.unlink(path)

    def test_register_with_explicit_id(self):
        explicit = uuid4()
        result = self.mapper.register("Account", "SF999", nexus_id=explicit)
        assert result == explicit


# ---------------------------------------------------------------------------
# SalesforceObjectMapper
# ---------------------------------------------------------------------------


class TestSalesforceObjectMapper:
    def test_map_account(self):
        sf_record = {
            "Id": "001SF",
            "Name": "Acme Corp",
            "Industry": "Technology",
            "Website": "https://acme.com",
            "Phone": "555-1234",
            "AnnualRevenue": "1000000",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Account", sf_record)
        assert result["name"] == "Acme Corp"
        assert result["_sf_id"] == "001SF"
        assert result["annual_revenue"] == 1000000.0

    def test_map_contact(self):
        sf_record = {
            "Id": "003SF",
            "FirstName": "Alice",
            "LastName": "Smith",
            "Email": "alice@acme.com",
            "AccountId": "001SF",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Contact", sf_record)
        assert result["first_name"] == "Alice"
        assert result["_sf_account_id"] == "001SF"

    def test_map_opportunity(self):
        sf_record = {
            "Id": "006SF",
            "Name": "Big Deal",
            "StageName": "Closed Won",
            "Amount": "50000",
            "CloseDate": "2025-12-31",
            "AccountId": "001SF",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Opportunity", sf_record)
        assert result["stage"] == "closed_won"
        assert result["amount"] == 50000.0

    def test_map_lead(self):
        sf_record = {
            "Id": "00QSF",
            "FirstName": "Bob",
            "LastName": "Jones",
            "Email": "bob@leads.com",
            "Company": "LeadCo",
            "Status": "Qualified",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Lead", sf_record)
        assert result["status"] == "qualified"

    def test_map_case(self):
        sf_record = {
            "Id": "500SF",
            "Subject": "Broken Widget",
            "Description": "It broke",
            "Status": "Working",
            "Priority": "High",
            "Origin": "Email",
            "AccountId": "001SF",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Case", sf_record)
        assert result["status"] == "in_progress"
        assert result["priority"] == "high"
        assert result["origin"] == "email"

    def test_missing_optional_fields(self):
        sf_record = {
            "Id": "001SF",
            "Name": "Minimal",
            "OwnerId": "005OWNER",
        }
        result = SalesforceObjectMapper.map_record("Account", sf_record)
        assert "website" not in result
        assert result["name"] == "Minimal"

    def test_required_field_missing_raises(self):
        sf_record = {"Id": "001SF"}  # Missing Name
        with pytest.raises(ValueError, match="Required field"):
            SalesforceObjectMapper.map_record("Contact", sf_record)


# ---------------------------------------------------------------------------
# Normalization Functions
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_normalise_stage_closed_won(self):
        assert _normalise_stage("Closed Won") == "closed_won"

    def test_normalise_stage_prospecting(self):
        assert _normalise_stage("Prospecting") == "prospecting"

    def test_normalise_stage_none(self):
        assert _normalise_stage(None) == "prospecting"

    def test_normalise_stage_unknown(self):
        assert _normalise_stage("Unknown Stage") == "prospecting"

    def test_normalise_lead_status_qualified(self):
        assert _normalise_lead_status("Qualified") == "qualified"

    def test_normalise_lead_status_none(self):
        assert _normalise_lead_status(None) == "new"

    def test_normalise_lead_status_unknown(self):
        assert _normalise_lead_status("Unknown") == "new"

    def test_normalise_case_priority_high(self):
        assert _normalise_case_priority("High") == "high"

    def test_normalise_case_priority_none(self):
        assert _normalise_case_priority(None) == "medium"

    def test_infer_territory_us(self):
        assert _infer_territory_region("US") == "Americas"

    def test_infer_territory_germany(self):
        assert _infer_territory_region("Germany") == "EMEA"

    def test_infer_territory_japan(self):
        assert _infer_territory_region("Japan") == "APAC"

    def test_infer_territory_unknown(self):
        assert _infer_territory_region("Atlantis") == "Americas"

    def test_infer_territory_none(self):
        assert _infer_territory_region(None) == "Americas"

    def test_normalise_case_origin(self):
        assert _normalise_case_origin("Email") == "email"

    def test_parse_amount_none(self):
        assert _parse_amount(None) == 0.0

    def test_parse_amount_valid(self):
        assert _parse_amount("12345.67") == 12345.67


# ---------------------------------------------------------------------------
# SalesforceDataSource
# ---------------------------------------------------------------------------


class TestSalesforceDataSource:
    def test_csv_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "Account.csv")
            with open(csv_path, "w") as f:
                f.write("Id,Name,Industry\n")
                f.write("001,Acme,Technology\n")
                f.write("002,Beta,Finance\n")

            ds = SalesforceDataSource(export_dir=tmpdir)
            records = ds.fetch_records("Account")
            assert len(records) == 2
            assert records[0]["Name"] == "Acme"

    def test_json_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "Contact.json")
            data = [
                {
                    "Id": "003",
                    "FirstName": "Alice",
                    "LastName": "Smith",
                    "Email": "a@b.com",
                    "AccountId": "001",
                }
            ]
            with open(json_path, "w") as f:
                json.dump(data, f)

            ds = SalesforceDataSource(export_dir=tmpdir)
            records = ds.fetch_records("Contact")
            assert len(records) == 1
            assert records[0]["FirstName"] == "Alice"

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "Account.csv")
            with open(csv_path, "w") as f:
                f.write("Id,Name\n")

            ds = SalesforceDataSource(export_dir=tmpdir)
            records = ds.fetch_records("Account")
            assert len(records) == 0

    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ds = SalesforceDataSource(export_dir=tmpdir)
            records = ds.fetch_records("Nonexistent")
            assert len(records) == 0


# ---------------------------------------------------------------------------
# SalesforceMigrator
# ---------------------------------------------------------------------------


class TestSalesforceMigrator:
    def test_dry_run_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal Account CSV
            with open(os.path.join(tmpdir, "Account.csv"), "w") as f:
                f.write("Id,Name,Industry,OwnerId\n")
                f.write("001,Acme,Technology,005OWN\n")

            config = MigrationConfig(
                export_dir=tmpdir,
                dry_run=True,
                output_dir=os.path.join(tmpdir, "output"),
                objects=["Account"],
            )
            migrator = SalesforceMigrator(config)
            results = migrator.migrate_all()
            assert "Account" in results
            assert results["Account"].succeeded == 1
            assert results["Account"].phase == MigrationPhase.COMPLETED

    def test_fk_resolution_contact_to_account(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "Account.csv"), "w") as f:
                f.write("Id,Name,Industry,OwnerId\n")
                f.write("001,Acme,Tech,005OWN\n")
            with open(os.path.join(tmpdir, "Contact.csv"), "w") as f:
                f.write("Id,FirstName,LastName,Email,AccountId,OwnerId\n")
                f.write("003,Alice,Smith,a@b.com,001,005OWN\n")

            config = MigrationConfig(
                export_dir=tmpdir,
                dry_run=True,
                output_dir=os.path.join(tmpdir, "output"),
                objects=["Account", "Contact"],
            )
            migrator = SalesforceMigrator(config)
            results = migrator.migrate_all()
            assert results["Contact"].succeeded == 1
            # Verify the FK was resolved
            contacts = migrator.get_migrated_records("Contact")
            assert len(contacts) == 1
            assert "account_id" in contacts[0]

    def test_error_collection_no_fail_fast(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Contact without Account → will fail FK resolution
            with open(os.path.join(tmpdir, "Contact.csv"), "w") as f:
                f.write("Id,FirstName,LastName,Email,AccountId,OwnerId\n")
                f.write("003,Alice,Smith,a@b.com,MISSING_ACCT,005OWN\n")
                f.write("004,Bob,Jones,b@c.com,MISSING_ACCT2,005OWN\n")

            config = MigrationConfig(
                export_dir=tmpdir,
                dry_run=True,
                output_dir=os.path.join(tmpdir, "output"),
                objects=["Contact"],
            )
            migrator = SalesforceMigrator(config)
            results = migrator.migrate_all()
            # Both should fail but not crash
            assert results["Contact"].failed == 2
            assert results["Contact"].succeeded == 0

    def test_migration_ordering(self):
        assert SalesforceMigrator.MIGRATION_ORDER == [
            "Account",
            "Contact",
            "Opportunity",
            "Lead",
            "Case",
        ]

    def test_progress_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "Account.csv"), "w") as f:
                f.write("Id,Name,Industry,OwnerId\n")
                f.write("001,A,Tech,005\n")
                f.write("002,B,Finance,005\n")
                f.write("003,C,Healthcare,005\n")

            config = MigrationConfig(
                export_dir=tmpdir,
                dry_run=True,
                output_dir=os.path.join(tmpdir, "output"),
                objects=["Account"],
            )
            migrator = SalesforceMigrator(config)
            results = migrator.migrate_all()
            prog = results["Account"]
            assert prog.total_records == 3
            assert prog.processed == 3
            assert prog.success_rate == 100.0
            assert prog.started_at is not None
            assert prog.completed_at is not None

    def test_format_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "Account.csv"), "w") as f:
                f.write("Id,Name,Industry,OwnerId\n")
                f.write("001,Acme,Tech,005\n")
            config = MigrationConfig(
                export_dir=tmpdir,
                dry_run=True,
                output_dir=os.path.join(tmpdir, "output"),
                objects=["Account"],
            )
            migrator = SalesforceMigrator(config)
            migrator.migrate_all()
            summary = migrator.format_summary()
            assert "Account" in summary
            assert "DRY RUN" in summary
