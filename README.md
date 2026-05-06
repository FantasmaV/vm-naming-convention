# vm-naming-convention

**Aria Automation ABX Action — Enterprise VM Naming Convention Enforcement**

Dynamically generates conflict-free, policy-compliant VM hostnames during provisioning in VMware Aria Automation.

---

## Naming Format

```
VM-{ENV}-{ROLE}-{LOCATION}-{SEQUENCE}
```

| Example | Environment | Role | Location | Sequence |
|---|---|---|---|---|
| `VM-PROD-WEB-TXD-001` | Production | Web Server | Texas Dallas | 001 |
| `VM-DEV-DB-NYC-042` | Development | Database | New York City | 042 |
| `VM-DR-SQL-TXH-007` | Disaster Recovery | SQL Server | Texas Houston | 007 |

---

## Allowed Values

| Category | Values |
|---|---|
| **Environment** | `PROD`, `DEV`, `TEST`, `UAT`, `STG`, `DR` |
| **Role** | `WEB`, `APP`, `DB`, `SQL`, `MGT`, `INF`, `MON`, `API`, `CAC`, `JMP` |
| **Location** | `TXD`, `TXH`, `NYC`, `LAX`, `CHI`, `ATL`, `DR1`, `DR2` |

---

## What it does

- Validates `environment`, `role`, and `location` against enterprise policy — raises immediately on violation
- Scans `existingVmNames` from the Aria blueprint to find the next available sequence number
- Fills sequence gaps before extending — if 001 and 003 exist, assigns 002
- Zero-pads sequence to 3 digits — `001`, `042`, `100`
- Detects and rejects duplicate names before returning

---

## Inputs / Outputs

**Inputs (from Aria blueprint):**

| Key | Type | Description |
|---|---|---|
| `environment` | string | Target environment code |
| `role` | string | VM role/tier code |
| `location` | string | Data center location code |
| `existingVmNames` | list | Existing VM names for sequence detection |

**Outputs:**

| Key | Type | Description |
|---|---|---|
| `vmName` | string | Generated hostname (e.g. `VM-PROD-WEB-TXD-001`) |
| `environment` | string | Validated environment |
| `role` | string | Validated role |
| `location` | string | Validated location |
| `sequence` | int | Assigned sequence number |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MAX_SEQUENCE` | `999` | Maximum sequence number per env/role/location combination |

---

## Running Tests

```bash
pip install pytest
pytest tests/test_vm_naming.py -v
```

---

## Author

**Randolph Barden** — [@FantasmaV](https://github.com/FantasmaV)

Senior VCF / Aria Automation Engineer | VMware by Broadcom

