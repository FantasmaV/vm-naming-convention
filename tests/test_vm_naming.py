"""
test_vm_naming.py
-----------------
Unit tests for the Aria Automation ABX Action — VM Naming Convention.

Tests cover input validation, sequence detection, name generation,
duplicate detection, and all error paths.

Run with:
    pytest tests/test_vm_naming.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../abx-actions'))
import vm_naming


# ── handler() tests ────────────────────────────────────────────────────────────

class TestHandler:

    def test_handler_returns_correct_name_no_existing(self):
        """handler() should return VM-PROD-WEB-TXD-001 when no existing VMs."""
        result = vm_naming.handler(context=None, inputs={
            "environment":    "PROD",
            "role":           "WEB",
            "location":       "TXD",
            "existingVmNames": []
        })
        assert result["vmName"]      == "VM-PROD-WEB-TXD-001"
        assert result["sequence"]    == 1
        assert result["environment"] == "PROD"
        assert result["role"]        == "WEB"
        assert result["location"]    == "TXD"

    def test_handler_increments_sequence_correctly(self):
        """handler() should return 002 when 001 already exists."""
        result = vm_naming.handler(context=None, inputs={
            "environment":    "PROD",
            "role":           "WEB",
            "location":       "TXD",
            "existingVmNames": ["VM-PROD-WEB-TXD-001"]
        })
        assert result["vmName"]   == "VM-PROD-WEB-TXD-002"
        assert result["sequence"] == 2

    def test_handler_fills_sequence_gap(self):
        """handler() should fill gap in sequence — 001 and 003 exist, returns 002."""
        result = vm_naming.handler(context=None, inputs={
            "environment":    "PROD",
            "role":           "WEB",
            "location":       "TXD",
            "existingVmNames": ["VM-PROD-WEB-TXD-001", "VM-PROD-WEB-TXD-003"]
        })
        assert result["vmName"]   == "VM-PROD-WEB-TXD-002"
        assert result["sequence"] == 2

    def test_handler_ignores_different_env_names(self):
        """handler() should ignore existing names from different environments."""
        result = vm_naming.handler(context=None, inputs={
            "environment":    "DEV",
            "role":           "WEB",
            "location":       "TXD",
            "existingVmNames": ["VM-PROD-WEB-TXD-001", "VM-PROD-WEB-TXD-002"]
        })
        assert result["vmName"]   == "VM-DEV-WEB-TXD-001"
        assert result["sequence"] == 1

    def test_handler_normalizes_lowercase_inputs(self):
        """handler() should normalize lowercase inputs to uppercase."""
        result = vm_naming.handler(context=None, inputs={
            "environment":    "prod",
            "role":           "web",
            "location":       "txd",
            "existingVmNames": []
        })
        assert result["vmName"] == "VM-PROD-WEB-TXD-001"

    def test_handler_raises_on_missing_environment(self):
        """handler() should raise KeyError if environment not in inputs."""
        with pytest.raises(KeyError, match="environment"):
            vm_naming.handler(context=None, inputs={
                "role":     "WEB",
                "location": "TXD"
            })

    def test_handler_raises_on_missing_role(self):
        """handler() should raise KeyError if role not in inputs."""
        with pytest.raises(KeyError, match="role"):
            vm_naming.handler(context=None, inputs={
                "environment": "PROD",
                "location":    "TXD"
            })

    def test_handler_raises_on_missing_location(self):
        """handler() should raise KeyError if location not in inputs."""
        with pytest.raises(KeyError, match="location"):
            vm_naming.handler(context=None, inputs={
                "environment": "PROD",
                "role":        "WEB"
            })

    def test_handler_defaults_existing_names_to_empty(self):
        """handler() should default existingVmNames to empty list if not provided."""
        result = vm_naming.handler(context=None, inputs={
            "environment": "PROD",
            "role":        "WEB",
            "location":    "TXD"
        })
        assert result["vmName"] == "VM-PROD-WEB-TXD-001"


# ── validate_inputs() tests ────────────────────────────────────────────────────

class TestValidateInputs:

    def test_valid_inputs_pass(self):
        """validate_inputs() should not raise for valid combinations."""
        vm_naming.validate_inputs("PROD", "WEB", "TXD")
        vm_naming.validate_inputs("DEV",  "DB",  "NYC")
        vm_naming.validate_inputs("DR",   "SQL", "DR1")

    def test_raises_on_invalid_environment(self):
        """validate_inputs() should raise ValueError for unknown environment."""
        with pytest.raises(ValueError, match="Invalid environment"):
            vm_naming.validate_inputs("STAGING", "WEB", "TXD")

    def test_raises_on_invalid_role(self):
        """validate_inputs() should raise ValueError for unknown role."""
        with pytest.raises(ValueError, match="Invalid role"):
            vm_naming.validate_inputs("PROD", "UNKNOWN", "TXD")

    def test_raises_on_invalid_location(self):
        """validate_inputs() should raise ValueError for unknown location."""
        with pytest.raises(ValueError, match="Invalid location"):
            vm_naming.validate_inputs("PROD", "WEB", "LON")

    def test_raises_with_multiple_errors(self):
        """validate_inputs() should report all violations at once."""
        with pytest.raises(ValueError) as exc_info:
            vm_naming.validate_inputs("BADENV", "BADROLE", "BADLOC")
        error_msg = str(exc_info.value)
        assert "environment" in error_msg.lower()
        assert "role"        in error_msg.lower()
        assert "location"    in error_msg.lower()

    def test_all_allowed_environments_pass(self):
        """All defined environments should pass validation."""
        for env in vm_naming.ALLOWED_ENVIRONMENTS:
            vm_naming.validate_inputs(env, "WEB", "TXD")

    def test_all_allowed_roles_pass(self):
        """All defined roles should pass validation."""
        for role in vm_naming.ALLOWED_ROLES:
            vm_naming.validate_inputs("PROD", role, "TXD")

    def test_all_allowed_locations_pass(self):
        """All defined locations should pass validation."""
        for loc in vm_naming.ALLOWED_LOCATIONS:
            vm_naming.validate_inputs("PROD", "WEB", loc)


# ── get_next_sequence() tests ──────────────────────────────────────────────────

class TestGetNextSequence:

    def test_returns_001_when_no_existing(self):
        """get_next_sequence() should return 1 when no existing VMs."""
        seq = vm_naming.get_next_sequence("PROD", "WEB", "TXD", [])
        assert seq == 1

    def test_returns_next_after_existing(self):
        """get_next_sequence() should return 3 when 001 and 002 exist."""
        seq = vm_naming.get_next_sequence(
            "PROD", "WEB", "TXD",
            ["VM-PROD-WEB-TXD-001", "VM-PROD-WEB-TXD-002"]
        )
        assert seq == 3

    def test_fills_gap_in_sequence(self):
        """get_next_sequence() should fill gap — 001 and 003 exist, returns 2."""
        seq = vm_naming.get_next_sequence(
            "PROD", "WEB", "TXD",
            ["VM-PROD-WEB-TXD-001", "VM-PROD-WEB-TXD-003"]
        )
        assert seq == 2

    def test_ignores_different_prefix(self):
        """get_next_sequence() should ignore names from different env/role/loc."""
        seq = vm_naming.get_next_sequence(
            "PROD", "APP", "TXD",
            ["VM-PROD-WEB-TXD-001", "VM-DEV-APP-TXD-001"]
        )
        assert seq == 1

    def test_raises_when_sequence_exhausted(self, monkeypatch):
        """get_next_sequence() should raise ValueError when all sequences used."""
        monkeypatch.setattr(vm_naming, "MAX_SEQUENCE", 3)
        existing = [
            "VM-PROD-WEB-TXD-001",
            "VM-PROD-WEB-TXD-002",
            "VM-PROD-WEB-TXD-003",
        ]
        with pytest.raises(ValueError, match="exhausted"):
            vm_naming.get_next_sequence("PROD", "WEB", "TXD", existing)

    def test_handles_mixed_case_existing_names(self):
        """get_next_sequence() should handle lowercase existing names gracefully."""
        seq = vm_naming.get_next_sequence(
            "PROD", "WEB", "TXD",
            ["vm-prod-web-txd-001"]
        )
        assert seq == 2


# ── generate_name() tests ──────────────────────────────────────────────────────

class TestGenerateName:

    def test_generates_correct_format(self):
        """generate_name() should produce VM-{ENV}-{ROLE}-{LOC}-{SEQ:03d}."""
        assert vm_naming.generate_name("PROD", "WEB", "TXD", 1)   == "VM-PROD-WEB-TXD-001"
        assert vm_naming.generate_name("DEV",  "DB",  "NYC", 42)  == "VM-DEV-DB-NYC-042"
        assert vm_naming.generate_name("DR",   "SQL", "TXH", 100) == "VM-DR-SQL-TXH-100"

    def test_pads_sequence_to_3_digits(self):
        """generate_name() should zero-pad sequence to 3 digits."""
        assert vm_naming.generate_name("PROD", "WEB", "TXD", 1)  == "VM-PROD-WEB-TXD-001"
        assert vm_naming.generate_name("PROD", "WEB", "TXD", 9)  == "VM-PROD-WEB-TXD-009"
        assert vm_naming.generate_name("PROD", "WEB", "TXD", 99) == "VM-PROD-WEB-TXD-099"
