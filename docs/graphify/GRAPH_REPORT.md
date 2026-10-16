# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1148 nodes · 3202 edges · 64 communities (48 shown, 16 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 406 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f570379`
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
- Community 44
- Community 46
- Community 47
- Community 48
- Community 49
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 57
- Community 58
- Community 59
- Community 63

## God Nodes (most connected - your core abstractions)
1. `Database` - 180 edges
2. `Settings` - 67 edges
3. `WebUser` - 65 edges
4. `AgentConfig` - 52 edges
5. `_html()` - 44 edges
6. `HardwareInfo` - 35 edges
7. `InventoryCollector` - 31 edges
8. `InventorySnapshot` - 28 edges
9. `ConfigCli` - 28 edges
10. `utc_now()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `check_update()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `delete_msi_version()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_settings_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_update_target_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `ingest_uploaded_msi()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py

## Import Cycles
- None detected.

## Communities (64 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (34): admin_token_valid(), authenticate_web_user(), ensure_bootstrap_secrets(), _persist(), load_ldap_view(), _read_secret_file(), require_admin_token(), require_api_key() (+26 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (32): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy() (+24 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (3): DeviceIdentity, ServiceCli, BadAgent

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (24): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (6): AsciiReportWriter, BadCli, HtmlReportWriter, IInventoryCollector, ReportFormat, ReportPathResolver

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (25): current_web_user(), get_data_key(), get_session_secret(), require_web_user(), encrypt_secret(), set_csrf_cookie(), _apply_bool_form_fields(), device_archive() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.20
Nodes (8): InventoryCollector, CollectorError, Error, Section, VolumeInfo, FreeBytes, Letter, SizeBytes

### Community 8 - "Community 8"
Cohesion: 0.15
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (10): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin() (+2 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 11 - "Community 11"
Cohesion: 0.20
Nodes (22): Settings, _backup_context(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), _device_config_context(), device_config_override_save(), device_detail_page() (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (21): require_web_admin(), dump_session(), load_session(), WebUser, devices_csv_export(), events_page(), _filter_policy_settings(), home() (+13 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (15): device_silence_status(), health_snippet(), parse_utc(), build_attention_queue(), build_bootstrap_checklist(), build_config_winner(), device_has_agent_local(), filter_devices_by_wave() (+7 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (24): CpuInfo, Cores, Logical, Name, DiskInfo, MediaType, Model, SizeBytes (+16 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (8): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today(), _add_file(), build_site_bundle(), _utc_stamp()

### Community 18 - "Community 18"
Cohesion: 0.19
Nodes (3): AgentUpdater, UpdatePlan, VersionUtil

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (17): ConfigLocalPayload, Keys, ServerUrl, Settings, RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings (+9 more)

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (18): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+10 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (14): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor, NetworkInfo, Nics (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (10): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), parse_semver(), resolve_target_msi() (+2 more)

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (7): enrollment_rotation_signals(), sensitive_over_http_blocked(), https_first_status(), merge_security_into_ops(), _secret_source(), secrets_status(), security_status()

### Community 26 - "Community 26"
Cohesion: 0.18
Nodes (7): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json()

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (10): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.22
Nodes (7): delete_msi_version(), ingest_uploaded_msi(), prune_old_msi_versions(), version_from_msi_name(), versions_pinned_in_config(), safe_msi_filename(), sha256_hex()

### Community 31 - "Community 31"
Cohesion: 0.26
Nodes (4): ConfigStore, ConfigPath, LogsDir, ProgramDataDir

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 34 - "Community 34"
Cohesion: 0.18
Nodes (3): set_latest_msi_version(), admin_agent_update_status(), agent_update_msi()

### Community 35 - "Community 35"
Cohesion: 0.28
Nodes (8): enrollment_status(), enrollment_token_file(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), generate_token(), hash_secret()

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (4): admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 44 - "Community 44"
Cohesion: 0.36
Nodes (6): _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test(), LdapFormData, _parse_ldap_form()

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 49 - "Community 49"
Cohesion: 0.29
Nodes (6): cookie_secure_for_request(), _clear_session_cookie(), logout(), password_submit(), render(), _set_session_cookie()

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (3): enroll(), inventory(), mark_device_enrolled()

### Community 55 - "Community 55"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (4): UpdateAction, Downgrade, None, Upgrade

## Knowledge Gaps
- **185 isolated node(s):** `CollectHardware`, `CollectSoftware`, `CollectUsers`, `AgentVersion`, `CollectedAt` (+180 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 385 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 8` to `Community 27`, `Community 19`, `Community 5`?**
  _High betweenness centrality (0.284) - this node is a cross-community bridge._
- **Are the 109 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 109 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CollectHardware`, `CollectSoftware`, `CollectUsers` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.052943354313217325 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 1` to `Community 0`, `Community 2`, `Community 6`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 15`, `Community 17`, `Community 24`, `Community 25`, `Community 30`, `Community 34`, `Community 35`, `Community 40`, `Community 43`, `Community 44`, `Community 49`, `Community 54`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09433962264150944 - nodes in this community are weakly interconnected._