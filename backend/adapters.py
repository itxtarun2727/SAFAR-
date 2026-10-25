"""
adapters.py — Pluggable Bank Integration Adapters.

⚠️ CRITICAL NOTICE:
All bank verification calls, confirmation responses, and tripartite feeds in this
prototype are SIMULATED using mock adapters for hackathon evaluation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import date, timedelta
from clock import Clock


class BaseBankAdapter(ABC):
    """Abstract interface for all core banking and nodal bank adapters."""

    @abstractmethod
    def verify(self, reference_no: str, bank_name: str) -> Dict[str, Any]:
        """Verify an FDR record against bank records."""
        pass

    @abstractmethod
    def fetch_daily_feed(self, target_date: date) -> List[Dict[str, Any]]:
        """Fetch batch daily reconciliation feed records."""
        pass

    @abstractmethod
    def request_release(self, reference_no: str, release_id: str) -> Dict[str, Any]:
        """Send lien release instruction to bank."""
        pass


class MockBankAdapter(BaseBankAdapter):
    """
    Simulated Bank Adapter (SIH Prototype).
    Provides deterministic responses for the 6 official demonstration scenarios.
    """

    def __init__(self):
        # In-memory bank simulator repository
        self.simulated_records: Dict[str, Dict[str, Any]] = {
            # Scenario 3: Matching active FDR (Delhi Institute)
            "SBIN00269910": {
                "reference_no": "SBIN00269910",
                "bank_name": "State Bank of India",
                "amount_paise": 250000000,
                "issue_date": "2024-01-15",
                "maturity_date": "2034-01-15",
                "joint_holder": "AICTE and Principal, Delhi Institute of Technology",
                "lien_marked": True,
                "status": "ACTIVE_AT_BANK",
            },
            # Scenario 2: Maturity date mismatch (Apex College)
            "HDFC00918273": {
                "reference_no": "HDFC00918273",
                "bank_name": "HDFC Bank",
                "amount_paise": 150000000,
                "issue_date": "2023-06-10",
                "maturity_date": "2028-06-10",  # College claimed 2033 (10 years) -> MISMATCH!
                "joint_holder": "AICTE and Apex College",
                "lien_marked": True,
                "status": "ACTIVE_AT_BANK",
                "mismatch_field": "maturity_date",
                "reason_code": "MATURITY_MISMATCH",
            },
            # Scenario 6: Disputed release candidate (Sunrise Institute)
            "ICIC00441188": {
                "reference_no": "ICIC00441188",
                "bank_name": "ICICI Bank",
                "amount_paise": 350000000,
                "issue_date": "2016-08-20",
                "maturity_date": "2026-08-20",
                "joint_holder": "AICTE and Sunrise Institute",
                "lien_marked": True,
                "status": "MATURED",
            },
            # Scenario 4: Approaching maturity in 30 days (National Polytechnic)
            "BARB00771239": {
                "reference_no": "BARB00771239",
                "bank_name": "Bank of Baroda",
                "amount_paise": 200000000,
                "issue_date": "2016-11-24",
                "maturity_date": "2026-11-24",
                "joint_holder": "AICTE and National Polytechnic",
                "lien_marked": True,
                "status": "ACTIVE_AT_BANK",
            },
        }

    def verify(self, reference_no: str, bank_name: str) -> Dict[str, Any]:
        """Simulate bank confirmation check."""
        record = self.simulated_records.get(reference_no)

        if not record:
            return {
                "result": "mismatch",
                "reason_code": "NOT_FOUND",
                "message": f"Instrument {reference_no} not found in {bank_name} records [SIMULATED].",
                "confirmed_data": None,
            }

        # Check for pre-programmed mismatches
        if "reason_code" in record:
            return {
                "result": "mismatch",
                "reason_code": record["reason_code"],
                "message": f"Bank record mismatch detected: {record['reason_code']} [SIMULATED].",
                "confirmed_data": record,
            }

        return {
            "result": "match",
            "reason_code": None,
            "message": "All fields and AICTE joint lien confirmed by issuing bank [SIMULATED].",
            "confirmed_data": record,
        }

    def fetch_daily_feed(self, target_date: date) -> List[Dict[str, Any]]:
        """Simulate a daily SFTP batch reconciliation feed from partner banks."""
        feed = []
        for ref, data in self.simulated_records.items():
            feed.append({
                "feed_date": target_date.isoformat(),
                "reference_no": ref,
                "bank_name": data["bank_name"],
                "amount_paise": data["amount_paise"],
                "maturity_date": data["maturity_date"],
                "lien_active": data.get("lien_marked", True),
                "bank_status": data.get("status", "ACTIVE"),
            })
        return feed

    def request_release(self, reference_no: str, release_id: str) -> Dict[str, Any]:
        """Simulate bank discharge acknowledgment."""
        return {
            "ack_id": f"BANK-REL-ACK-{release_id[:8]}",
            "reference_no": reference_no,
            "status": "DISCHARGE_CONFIRMED_SIMULATED",
            "message": "AICTE joint lien discharged and funds release confirmed [SIMULATED].",
            "timestamp": Clock.now().isoformat(),
        }


class FileFeedAdapter:
    """Parser for batch CSV/Excel bank reconciliation drops."""

    @staticmethod
    def parse_csv_feed(csv_content: str) -> List[Dict[str, Any]]:
        """Parse raw CSV records into structured bank feed entries."""
        lines = [line.strip() for line in csv_content.strip().split("\n") if line.strip()]
        if not lines:
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        records = []
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == len(headers):
                records.append(dict(zip(headers, parts)))
        return records


# Default singleton instance
bank_adapter: BaseBankAdapter = MockBankAdapter()
