# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1038 nodes · 2840 edges · 62 communities (43 shown, 19 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 385 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b08c3b4b`
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
- Community 41
- Community 42
- Community 43
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 51
- Community 53
- Community 54
- Community 55
- Community 56
- Community 61

## God Nodes (most connected - your core abstractions)
1. `Database` - 172 edges
2. `WebUser` - 65 edges
3. `Settings` - 54 edges
4. `_html()` - 41 edges
5. `HardwareInfo` - 35 edges
6. `AgentConfig` - 35 edges
7. `InventoryCollector` - 31 edges
8. `InventorySnapshot` - 28 edges
9. `utc_now()` - 23 edges
10. `BadAgent` - 21 edges

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

## Communities (62 total, 19 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (83): current_web_user(), get_data_key(), get_db(), get_session_secret(), require_web_admin(), require_web_user(), Settings, cookie_secure_for_request() (+75 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (3): list_devices(), Database, utc_now()

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (32): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy() (+24 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (17): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir() (+9 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (9): AsciiReportWriter, BadCli, HtmlReportWriter, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, IInventoryCollector (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (5): InventoryCollector, CollectorError, Error, Section, WmiHelper

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (19): apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z(), key_path(), _load_size_check(), _normalize_pem() (+11 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (11): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings() (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (20): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (13): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals(), parse_semver() (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (24): DiskInfo, MediaType, Model, SizeBytes, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (11): load_ldap_view(), authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server() (+3 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (11): admin_token_valid(), authenticate_web_user(), require_admin_token(), require_api_key(), require_enrollment_token(), try_ldap_login(), try_local_login(), api_key_lookup() (+3 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (7): delete_msi_version(), prune_old_msi_versions(), versions_pinned_in_config(), admin_agent_update_delete(), admin_agent_update_status(), agent_update_msi(), sort_key()

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (11): build_alert_email(), build_inventory_events_email(), _dispatch(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device(), parse_notify_flags() (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (14): InstalledProgram, Name, Publisher, Version, NetworkInfo, Nics, NicInfo, Dhcp (+6 more)

### Community 20 - "Community 20"
Cohesion: 0.26
Nodes (10): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin() (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (7): enrollment_status(), enrollment_token_file(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), generate_token()

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (10): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (8): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk, SystemDriveFreeBytes

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (15): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.26
Nodes (5): generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (9): devices, idx_snapshots_device_received, inventory_snapshots, site_secrets, agent_policies, device_config_overrides, device_events, idx_device_events_created (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 40 - "Community 40"
Cohesion: 0.39
Nodes (3): decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 42 - "Community 42"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (3): admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 53 - "Community 53"
Cohesion: 0.50
Nodes (4): CpuInfo, Cores, Logical, Name

## Knowledge Gaps
- **178 isolated node(s):** `MetaPath`, `QueueDir`, `Attempts`, `Body`, `CreatedAtUtc` (+173 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 356 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 7` to `Community 16`, `Community 9`, `Community 4`, `Community 22`?**
  _High betweenness centrality (0.263) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 103 INFERRED edges - model-reasoned connections that need verification._
- **What connects `MetaPath`, `QueueDir`, `Attempts` to the rest of the system?**
  _178 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05693176879617558 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 10`, `Community 42`, `Community 13`, `Community 14`, `Community 15`, `Community 49`, `Community 20`, `Community 52`, `Community 21`?**
  _High betweenness centrality (0.221) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.1012987012987013 - nodes in this community are weakly interconnected._