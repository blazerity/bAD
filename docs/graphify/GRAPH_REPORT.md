# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1280 nodes · 3717 edges · 68 communities (45 shown, 23 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 458 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e4edf989`
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
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 67

## God Nodes (most connected - your core abstractions)
1. `Database` - 187 edges
2. `Settings` - 101 edges
3. `WebUser` - 77 edges
4. `AgentConfig` - 52 edges
5. `_html()` - 47 edges
6. `HardwareInfo` - 35 edges
7. `utc_now()` - 32 edges
8. `InventoryCollector` - 31 edges
9. `InventorySnapshot` - 28 edges
10. `ConfigCli` - 28 edges

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

## Communities (68 total, 23 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (100): authenticate_web_user(), current_web_user(), load_ldap_view(), require_web_admin(), try_ldap_login(), Settings, encrypt_secret(), cookie_secure_for_request() (+92 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (32): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (5): enroll(), inventory(), Database, utc_now(), mark_device_enrolled()

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (35): admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token() (+27 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (18): sanitize_update_target(), check_update(), delete_msi_version(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals() (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (24): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+16 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (29): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy() (+21 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (21): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename() (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (9): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file() (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.28
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (5): adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), _split_sql_statements()

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (24): CpuInfo, Cores, Logical, Name, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (13): admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token(), require_web_user() (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (12): AgentApiException, IsAuthFailure, OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures (+4 more)

### Community 22 - "Community 22"
Cohesion: 0.24
Nodes (11): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin() (+3 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (4): ConfigStore, ConfigPath, LogsDir, ProgramDataDir

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (18): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+10 more)

### Community 25 - "Community 25"
Cohesion: 0.14
Nodes (12): DiskInfo, MediaType, Model, SizeBytes, NetworkInfo, Nics, NicInfo, Dhcp (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (8): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), _fernet_from_key(), generate_data_key(), generate_session_secret()

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.35
Nodes (14): archive_current_slot(), download_and_fill_slot(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots(), read_request() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.20
Nodes (4): ConfigLocalPayload, Keys, ServerUrl, Settings

### Community 36 - "Community 36"
Cohesion: 0.23
Nodes (3): admin_set_device_override(), get_device(), list_devices()

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (5): https_first_status(), merge_security_into_ops(), _secret_source(), secrets_status(), security_status()

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.29
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 49 - "Community 49"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 50 - "Community 50"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 53 - "Community 53"
Cohesion: 0.29
Nodes (4): admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 59 - "Community 59"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

## Knowledge Gaps
- **185 isolated node(s):** `Error`, `Section`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+180 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 405 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 9` to `Community 19`, `Community 21`, `Community 31`?**
  _High betweenness centrality (0.274) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 114 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Error`, `Section`, `CollectHardware` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.051835396170527875 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 2` to `Community 0`, `Community 1`, `Community 36`, `Community 4`, `Community 6`, `Community 40`, `Community 8`, `Community 10`, `Community 14`, `Community 18`, `Community 53`, `Community 22`, `Community 26`, `Community 61`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Are the 89 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 89 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05834464043419267 - nodes in this community are weakly interconnected._