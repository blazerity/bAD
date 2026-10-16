# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1101 nodes · 3056 edges · 59 communities (43 shown, 16 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 389 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f0bf89f`
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
- Community 39
- Community 40
- Community 41
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
- Community 54
- Community 58

## God Nodes (most connected - your core abstractions)
1. `Database` - 172 edges
2. `WebUser` - 65 edges
3. `Settings` - 59 edges
4. `AgentConfig` - 51 edges
5. `_html()` - 44 edges
6. `HardwareInfo` - 35 edges
7. `InventoryCollector` - 31 edges
8. `ConfigCli` - 28 edges
9. `InventorySnapshot` - 28 edges
10. `utc_now()` - 23 edges

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

## Communities (59 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (89): authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), load_ldap_view(), require_web_admin(), require_web_user() (+81 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (28): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+20 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (20): _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), ensure_bootstrap_secrets(), _persist() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (24): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (6): AsciiReportWriter, BadCli, HtmlReportWriter, IInventoryCollector, ReportFormat, ReportPathResolver

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (8): InventoryCollector, CollectorError, Error, Section, VolumeInfo, FreeBytes, Letter, SizeBytes

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (26): DiskInfo, MediaType, Model, SizeBytes, GpuInfo, AdapterRamBytes, DriverVersion, Name (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 12 - "Community 12"
Cohesion: 0.18
Nodes (13): admin_create_policy(), admin_set_device_override(), admin_update_policy(), put_device_tags(), AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (8): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today(), _add_file(), build_site_bundle(), _utc_stamp()

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.20
Nodes (3): AgentUpdater, UpdatePlan, VersionUtil

### Community 17 - "Community 17"
Cohesion: 0.10
Nodes (18): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, CpuInfo, Cores (+10 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (10): check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), parse_semver(), resolve_target_msi(), _semver_equal() (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.18
Nodes (9): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename() (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (9): admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_enrollment_rotate(), archive_device(), restore_device(), revoke_device(), Database (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (7): enroll(), inventory(), rotate_device_key(), seed_default_admin(), api_key_lookup(), generate_token(), hash_secret()

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (10): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+2 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (3): site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 27 - "Community 27"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.19
Nodes (3): delete_msi_version(), admin_agent_update_status(), agent_update_msi()

### Community 30 - "Community 30"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (7): admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), constant_time_equals(), extract_bearer(), verify_secret()

### Community 33 - "Community 33"
Cohesion: 0.17
Nodes (5): ingest_uploaded_msi(), prune_old_msi_versions(), sync_from_github(), version_from_msi_name(), versions_pinned_in_config()

### Community 34 - "Community 34"
Cohesion: 0.24
Nodes (9): admin_agent_config_defaults(), admin_device_config(), admin_get_policy(), admin_list_policies(), agent_config(), agent_update_check(), get_device(), health() (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (4): device_silence_status(), health_snippet(), normalize_tags(), parse_utc()

### Community 39 - "Community 39"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 41 - "Community 41"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.22
Nodes (4): admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (4): UpdateAction, Downgrade, None, Upgrade

## Knowledge Gaps
- **185 isolated node(s):** `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+180 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 368 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 6` to `Community 24`, `Community 1`, `Community 4`?**
  _High betweenness centrality (0.294) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 103 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentLocalKeys`, `ApiKey`, `CollectHardware` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.052780511811023625 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 22` to `Community 0`, `Community 33`, `Community 34`, `Community 2`, `Community 32`, `Community 11`, `Community 12`, `Community 44`, `Community 13`, `Community 15`, `Community 18`, `Community 23`, `Community 26`, `Community 29`?**
  _High betweenness centrality (0.205) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0624048706240487 - nodes in this community are weakly interconnected._