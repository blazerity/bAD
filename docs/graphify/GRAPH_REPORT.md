# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 987 nodes · 2696 edges · 60 communities (41 shown, 19 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 381 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8a7090cf`
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
- Community 40
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 59

## God Nodes (most connected - your core abstractions)
1. `Database` - 172 edges
2. `WebUser` - 61 edges
3. `Settings` - 54 edges
4. `_html()` - 40 edges
5. `HardwareInfo` - 35 edges
6. `AgentConfig` - 35 edges
7. `InventoryCollector` - 31 edges
8. `InventorySnapshot` - 28 edges
9. `BadAgent` - 21 edges
10. `CollectorError` - 20 edges

## Surprising Connections (you probably didn't know these)
- `delete_msi_version()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `ingest_uploaded_msi()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `prune_old_msi_versions()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `sync_from_github()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `admin_agent_update_delete()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py

## Import Cycles
- None detected.

## Communities (60 total, 19 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (86): authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), load_ldap_view(), require_web_admin(), require_web_user() (+78 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (27): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), admin_token_valid() (+19 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (29): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy() (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (9): AsciiReportWriter, BadCli, HtmlReportWriter, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, IInventoryCollector (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (3): try_local_login(), Database, utc_now()

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (5): InventoryCollector, CollectorError, Error, Section, WmiHelper

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (20): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+12 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (7): delete_msi_version(), effective_settings_for_device(), ops_update_signals(), prune_old_msi_versions(), versions_pinned_in_config(), admin_agent_update_delete(), admin_agent_update_status()

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (24): DiskInfo, MediaType, Model, SizeBytes, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.16
Nodes (9): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings() (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.22
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (4): enrollment_token_file(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (14): InstalledProgram, Name, Publisher, Version, NetworkInfo, Nics, NicInfo, Dhcp (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (9): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.19
Nodes (10): sanitize_update_target(), check_update(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), parse_semver(), resolve_target_msi(), _semver_equal() (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.21
Nodes (3): admin_delete_device_override(), get_device(), list_devices()

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (8): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk, SystemDriveFreeBytes

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (15): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (10): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+2 more)

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.35
Nodes (5): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today()

### Community 31 - "Community 31"
Cohesion: 0.23
Nodes (9): devices, idx_snapshots_device_received, inventory_snapshots, site_secrets, agent_policies, device_config_overrides, device_events, idx_device_events_created (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.31
Nodes (3): _add_file(), build_site_bundle(), _utc_stamp()

### Community 36 - "Community 36"
Cohesion: 0.31
Nodes (3): device_silence_status(), health_snippet(), parse_utc()

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 42 - "Community 42"
Cohesion: 0.38
Nodes (4): enroll(), rotate_device_key(), api_key_lookup(), generate_token()

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 44 - "Community 44"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (4): CpuInfo, Cores, Logical, Name

## Knowledge Gaps
- **178 isolated node(s):** `MediaType`, `Model`, `SizeBytes`, `Battery`, `BiosManufacturer` (+173 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 346 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 6` to `Community 16`, `Community 3`, `Community 14`, `Community 7`?**
  _High betweenness centrality (0.269) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 103 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MediaType`, `Model`, `SizeBytes` to the rest of the system?**
  _178 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05049368828896388 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 35`, `Community 9`, `Community 42`, `Community 13`, `Community 47`, `Community 16`, `Community 49`, `Community 19`, `Community 20`, `Community 53`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Are the 51 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07213114754098361 - nodes in this community are weakly interconnected._