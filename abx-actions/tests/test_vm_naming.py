"""
vm_naming.py
------------
Aria Automation ABX Action — Enterprise VM Naming Convention Enforcement

Dynamically generates standardized, conflict-free VM hostnames following
the enterprise naming convention:

    VM-{ENV}-{ROLE}-{LOCATION}-{SEQUENCE}

Examples:
    VM-PROD-WEB-TXD-001
    VM-DEV-DB-NYC-042
    VM-DR-SQL-TXH-007

The action validates all inputs against allowed values, queries existing
VM names passed from the Aria blueprint to determine the next available
sequence number, and raises immediately on any naming policy violation.

Environment Variables (set in Aria Automation ABX Action properties):
    MAX_SEQUENCE    Maximum sequence number allowed (default: 999)

Inputs (from Aria blueprint):
    environment     Target environment (PROD, DEV, TEST, UAT, STG, DR)
    role            VM role/tier (WEB, APP, DB, SQL, MGT, INF, MON, API, CAC, JMP)
    location        Data center location code (TXD, TXH, NYC, LAX, CHI, ATL, DR1, DR2)
    existingVmNames List of existing VM names in the target environment (for sequence detection)

Author: Randolph Barden
Repo:   github.com/FantasmaV/vm-naming-convention
"""

import os
import re
import logging

# ── Logging ────────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Policy Definitions ─────────────────────────────────────────────────────────
ALLOWED_ENVIRONMENTS = {"PROD", "DEV", "TEST", "UAT", "STG", "DR"}

ALLOWED_ROLES = {
    "WEB",   # Web / Frontend servers
    "APP",   # Application servers
    "DB",    # Database servers (generic)
    "SQL",   # Microsoft SQL Server
    "MGT",   # Management / Admin
    "INF",   # Infrastructure services
    "MON",   # Monitoring / Observability
    "API",   # API Gateway / Microservices
    "CAC",   # Cache servers (Redis, Memcached)
    "JMP",   # Jump / Bastion hosts
}

ALLOWED_LOCATIONS = {
    "TXD",   # Texas — Dallas
    "TXH",   # Texas — Houston
    "NYC",   # New York City
    "LAX",   # Los Angeles
    "CHI",   # Chicago
    "ATL",   # Atlanta
    "DR1",   # Disaster Recovery Site 1
    "DR2",   # Disaster Recovery Site 2
}

MAX_SEQUENCE = int(os.environ.get("MAX_SEQUENCE", "999"))

# Compiled pattern for matching existing VM names in the naming convention format
# Matches: VM-{ENV}-{ROLE}-{LOCATION}-{3-digit sequence}
_NAME_PATTERN = re.compile(
    r"^VM-(?P<env>[A-Z]+)-(?P<role>[A-Z]+)-(?P<loc>[A-Z0-9]+)-(?P<seq>\d{3})$"
)


# ── ABX Entry Point ────────────────────────────────────────────────────────────
def handler(context, inputs: dict) -> dict:
    """
    ABX handler called by Aria Automation during VM provisioning.

    Validates naming policy inputs, determines the next available sequence
    number from existing VM names, and returns the fully formatted hostname.

    Args:
        context: Aria Automation execution context (unused directly).
        inputs:  Dictionary of inputs passed from the Aria blueprint.
                 Expected keys:
                   - environment (str):      Target environment code.
                   - role (str):             VM role/tier code.
                   - location (str):         Data center location code.
                   - existingVmNames (list): List of existing VM name strings
                                             for duplicate/sequence detection.

    Returns:
        dict with keys:
          - vmName (str):       The generated VM hostname.
          - environment (str):  Validated environment code.
          - role (str):         Validated role code.
          - location (str):     Validated location code.
          - sequence (int):     The assigned sequence number.

    Raises:
        ValueError: If any input fails policy validation or sequence is exhausted.
        KeyError:   If required inputs are missing from the blueprint.
    """
    logger.info("[naming] Starting VM name generation")

    # ── Extract and normalize inputs ───────────────────────────────────────────
    try:
        environment = inputs["environment"].strip().upper()
        role        = inputs["role"].strip().upper()
        location    = inputs["location"].strip().upper()
    except KeyError as e:
        raise KeyError(f"Required input missing from blueprint: {e}")

    existing_names = inputs.get("existingVmNames", [])
    if not isinstance(existing_names, list):
        raise ValueError(
            f"'existingVmNames' must be a list of strings, got {type(existing_names).__name__}"
        )

    logger.info(f"[naming] Inputs — ENV: {environment} | ROLE: {role} | LOC: {location}")
    logger.info(f"[naming] Existing VM names provided: {len(existing_names)}")

    # ── Validate inputs against policy ────────────────────────────────────────
    validate_inputs(environment, role, location)

    # ── Determine next sequence number ────────────────────────────────────────
    sequence = get_next_sequence(environment, role, location, existing_names)

    # ── Generate hostname ─────────────────────────────────────────────────────
    vm_name = generate_name(environment, role, location, sequence)

    # ── Final duplicate check ─────────────────────────────────────────────────
    if vm_name in existing_names:
        raise ValueError(
            f"Generated name '{vm_name}' already exists in the provided VM inventory. "
            f"This indicates a sequence detection error — review existingVmNames input."
        )

    logger.info(f"[naming] Successfully generated VM name: {vm_name}")

    return {
        "vmName":      vm_name,
        "environment": environment,
        "role":        role,
        "location":    location,
        "sequence":    sequence,
    }


# ── Validation ─────────────────────────────────────────────────────────────────
def validate_inputs(environment: str, role: str, location: str) -> None:
    """
    Validate all naming convention inputs against the enterprise policy definitions.

    Args:
        environment: Environment code string (e.g. 'PROD').
        role:        Role code string (e.g. 'WEB').
        location:    Location code string (e.g. 'TXD').

    Raises:
        ValueError: If any value is not in the allowed set for its category.
    """
    errors = []

    if environment not in ALLOWED_ENVIRONMENTS:
        errors.append(
            f"Invalid environment '{environment}'. "
            f"Allowed values: {sorted(ALLOWED_ENVIRONMENTS)}"
        )

    if role not in ALLOWED_ROLES:
        errors.append(
            f"Invalid role '{role}'. "
            f"Allowed values: {sorted(ALLOWED_ROLES)}"
        )

    if location not in ALLOWED_LOCATIONS:
        errors.append(
            f"Invalid location '{location}'. "
            f"Allowed values: {sorted(ALLOWED_LOCATIONS)}"
        )

    if errors:
        raise ValueError(
            "VM naming policy violation — the following inputs are invalid:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

    logger.info(f"[naming] Input validation passed — {environment}/{role}/{location}")


# ── Sequence Detection ─────────────────────────────────────────────────────────
def get_next_sequence(
    environment: str,
    role: str,
    location: str,
    existing_names: list
) -> int:
    """
    Determine the next available sequence number for the given
    environment + role + location combination.

    Scans the provided list of existing VM names, extracts all sequence
    numbers that match the target prefix, and returns the next integer
    after the highest found. Starts at 1 if no matches exist.

    Args:
        environment:    Validated environment code.
        role:           Validated role code.
        location:       Validated location code.
        existing_names: List of existing VM hostname strings.

    Returns:
        int: Next available sequence number (1–MAX_SEQUENCE).

    Raises:
        ValueError: If the sequence pool for this combination is exhausted.
    """
    prefix = f"VM-{environment}-{role}-{location}-"
    used_sequences = set()

    for name in existing_names:
        name = name.strip().upper()
        match = _NAME_PATTERN.match(name)
        if match:
            if (
                match.group("env")  == environment and
                match.group("role") == role and
                match.group("loc")  == location
            ):
                used_sequences.add(int(match.group("seq")))

    logger.info(
        f"[naming] Found {len(used_sequences)} existing VMs with prefix '{prefix}': "
        f"{sorted(used_sequences) if used_sequences else 'none'}"
    )

    # Find next available sequence — fills gaps before extending
    for seq in range(1, MAX_SEQUENCE + 1):
        if seq not in used_sequences:
            logger.info(f"[naming] Next available sequence: {seq:03d}")
            return seq

    raise ValueError(
        f"Sequence pool exhausted for VM-{environment}-{role}-{location}. "
        f"All {MAX_SEQUENCE} sequences (001–{MAX_SEQUENCE:03d}) are in use. "
        f"Contact your infrastructure team to review VM inventory or increase MAX_SEQUENCE."
    )


# ── Name Generation ────────────────────────────────────────────────────────────
def generate_name(environment: str, role: str, location: str, sequence: int) -> str:
    """
    Assemble the final VM hostname from validated components.

    Format: VM-{ENV}-{ROLE}-{LOCATION}-{SEQ:03d}
    Example: VM-PROD-WEB-TXD-001

    Args:
        environment: Validated environment code.
        role:        Validated role code.
        location:    Validated location code.
        sequence:    Integer sequence number (will be zero-padded to 3 digits).

    Returns:
        str: Fully formatted VM hostname string.
    """
    name = f"VM-{environment}-{role}-{location}-{sequence:03d}"
    logger.info(f"[naming] Generated hostname: {name}")
    return name
