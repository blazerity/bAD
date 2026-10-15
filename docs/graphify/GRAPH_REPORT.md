# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 850 nodes · 2317 edges · 32 communities (22 shown, 10 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 319 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `12b315f2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 31

## God Nodes (most connected - your core abstractions)
1. `Database` - 140 edges
2. `WebUser` - 52 edges
3. `Settings` - 33 edges
4. `HardwareInfo` - 30 edges
5. `AgentConfig` - 30 edges
6. `InventorySnapshot` - 27 edges
7. `InventoryCollector` - 26 edges
8. `enroll_device()` - 23 edges
9. `diff_inventory_snapshots()` - 20 edges
10. `BadAgent` - 20 edges

## Surprising Connections (you probably didn't know these)
- `sync_from_github()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `_agent_update_sync_loop()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py
- `_backup_loop()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py
- `lifespan()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py
- `_retention_prune_loop()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py

## Import Cycles
- None detected.

## Communities (32 total, 10 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (33): check_update(), admin_agent_config_defaults(), admin_agent_update_status(), admin_agent_update_sync(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy(), admin_device_config() (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (30): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), admin_token_valid() (+22 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (56): authenticate_web_user(), load_ldap_view(), require_web_admin(), try_ldap_login(), Settings, encrypt_secret(), dump_session(), WebUser (+48 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (37): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (30): is_newer(), parse_semver(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (32): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today(), enroll_device(), test_enroll_inventory_get_flow(), test_health() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (24): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings() (+16 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (4): DeviceIdentity, WmiHelper, BadAgent, BadAgent.Tests

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (21): device_silence_status(), health_snippet(), normalize_tags(), parse_utc(), _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots() (+13 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.28
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (3): AsciiReportWriter, HtmlReportWriter, ReportFormat

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (18): BadAgent, net8.0, BadAgent.Tests, coverlet.collector (6.0.0), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.NET.Test.Sdk (17.8.0), Microsoft.Win32.Registry (5.0.0) (+10 more)

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (3): CollectorTests, FakeCollector, UpdateAndServiceTests

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (19): DiskInfo, MediaType, Model, SizeBytes, HardwareInfo, Cpu, Disks, Gpus (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (16): CpuInfo, Cores, Logical, Name, GpuInfo, AdapterRamBytes, DriverVersion, Name (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (10): HostInfo, Domain, Hostname, Os, OsInfo, Arch, Build, Caption (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 26 - "Community 26"
Cohesion: 0.33
Nodes (6): NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 27 - "Community 27"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

## Knowledge Gaps
- **115 isolated node(s):** `Error`, `Section`, `coverlet.collector (6.0.0)`, `Microsoft.Extensions.Hosting (8.0.1)`, `Microsoft.Extensions.Hosting.WindowsServices (8.0.1)` (+110 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 245 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 3` to `Community 18`, `Community 19`, `Community 14`, `Community 22`?**
  _High betweenness centrality (0.356) - this node is a cross-community bridge._
- **Are the 77 inferred relationships involving `Database` (e.g. with `check_update()` and `sync_from_github()`) actually correct?**
  _`Database` has 77 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Error`, `Section`, `coverlet.collector (6.0.0)` to the rest of the system?**
  _115 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.059157509157509156 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.197) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05485232067510549 - nodes in this community are weakly interconnected._