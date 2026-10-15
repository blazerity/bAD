# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 879 nodes · 2314 edges · 44 communities (35 shown, 9 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 304 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `51a05eac`
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
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 43

## God Nodes (most connected - your core abstractions)
1. `Database` - 141 edges
2. `WebUser` - 54 edges
3. `Settings` - 38 edges
4. `HardwareInfo` - 35 edges
5. `_html()` - 35 edges
6. `InventoryCollector` - 31 edges
7. `AgentConfig` - 28 edges
8. `InventorySnapshot` - 28 edges
9. `BadAgent` - 21 edges
10. `CollectorError` - 20 edges

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

## Communities (44 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (31): check_update(), admin_agent_config_defaults(), admin_agent_update_status(), admin_agent_update_sync(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy(), admin_device_config() (+23 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (61): require_web_admin(), Settings, encrypt_secret(), cookie_secure_for_request(), set_csrf_cookie(), dump_session(), WebUser, _apply_bool_form_fields() (+53 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (27): is_newer(), parse_semver(), sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop() (+19 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (4): DeviceIdentity, ReportPathResolver, ServiceCli, BadAgent

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (20): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings() (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (5): InventoryCollector, CollectorError, Error, Section, WmiHelper

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (8): BadCli, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, IInventoryCollector, UpdatePathUtil, VersionUtil

### Community 7 - "Community 7"
Cohesion: 0.20
Nodes (3): AgentUpdater, BadApiClient, Worker

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (12): load_ldap_view(), try_ldap_login(), authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn() (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (24): DiskInfo, MediaType, Model, SizeBytes, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (17): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (3): AsciiReportWriter, HtmlReportWriter, ReportFormat

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (15): admin_token_valid(), authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key() (+7 more)

### Community 14 - "Community 14"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (11): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, HeartbeatIntervalMinutes (+3 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (14): InstalledProgram, Name, Publisher, Version, NetworkInfo, Nics, NicInfo, Dhcp (+6 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (12): AgentApiException, IsAuthFailure, OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (15): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 23 - "Community 23"
Cohesion: 0.23
Nodes (9): devices, idx_snapshots_device_received, inventory_snapshots, site_secrets, agent_policies, device_config_overrides, device_events, idx_device_events_created (+1 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.20
Nodes (6): UpdateCheckResponse, MsiName, Sha256, UpdateAvailable, Url, Version

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 29 - "Community 29"
Cohesion: 0.28
Nodes (6): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key(), generate_session_secret()

### Community 30 - "Community 30"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 31 - "Community 31"
Cohesion: 0.25
Nodes (8): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk, SystemDriveFreeBytes

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 37 - "Community 37"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 38 - "Community 38"
Cohesion: 0.50
Nodes (4): CpuInfo, Cores, Logical, Name

## Knowledge Gaps
- **166 isolated node(s):** `MediaType`, `Model`, `SizeBytes`, `Battery`, `BiosManufacturer` (+161 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 302 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 7` to `Community 11`, `Community 17`, `Community 3`, `Community 6`?**
  _High betweenness centrality (0.270) - this node is a cross-community bridge._
- **Are the 79 inferred relationships involving `Database` (e.g. with `check_update()` and `sync_from_github()`) actually correct?**
  _`Database` has 79 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MediaType`, `Model`, `SizeBytes` to the rest of the system?**
  _166 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05934065934065934 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 9`, `Community 13`, `Community 29`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07983193277310924 - nodes in this community are weakly interconnected._