# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1216 nodes · 3387 edges · 67 communities (49 shown, 18 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 416 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `237045b9`
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
- Community 45
- Community 46
- Community 47
- Community 48
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 61
- Community 62
- Community 66

## God Nodes (most connected - your core abstractions)
1. `Database` - 191 edges
2. `Settings` - 70 edges
3. `WebUser` - 67 edges
4. `AgentConfig` - 52 edges
5. `_html()` - 46 edges
6. `HardwareInfo` - 35 edges
7. `InventoryCollector` - 31 edges
8. `ConfigCli` - 28 edges
9. `InventorySnapshot` - 28 edges
10. `utc_now()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Database` --uses--> `CompatConnection`  [INFERRED]
  server/bad_server/db.py → server/bad_server/db_backend.py
- `require_web_user()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/sessions.py
- `_backup_context()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py
- `backups_key_escrow_download()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py
- `backups_settings_page()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py

## Import Cycles
- None detected.

## Communities (67 total, 18 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (31): _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), ensure_bootstrap_secrets(), _persist() (+23 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (28): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+20 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (11): adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), connect_sqlite(), _split_sql_statements(), cli(), import_sqlite_to_postgres() (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (26): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_create_policy(), admin_enrollment_rotate(), admin_get_policy(), admin_security_status(), admin_set_device_override() (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (6): AsciiReportWriter, BadCli, HtmlReportWriter, IInventoryCollector, ReportFormat, ReportPathResolver

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (22): enroll_cleartext_blocked(), request_is_cleartext(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url(), _iso_z() (+14 more)

### Community 6 - "Community 6"
Cohesion: 0.11
Nodes (5): admin_delete_policy(), admin_list_policies(), try_local_login(), Database, utc_now()

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (18): Settings, enrollment_rotation_signals(), enrollment_status(), sensitive_over_http_blocked(), tls_mode_http(), https_first_status(), merge_security_into_ops(), _secret_source() (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (17): backup_filename_pg(), backup_filename_sqlite(), backup_status(), _chmod_private(), list_backup_files(), _ok_backup(), _pg_dump_env(), _prune_old() (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (26): get_data_key(), get_db(), get_session_secret(), require_web_user(), encrypt_secret(), _clear_session_cookie(), device_archive(), device_delete() (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (23): backup_keys_status(), health_snippet(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), _device_config_context() (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (14): device_silence_status(), parse_utc(), build_attention_queue(), build_bootstrap_checklist(), build_config_winner(), device_has_agent_local(), filter_devices_by_wave(), _match() (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (8): enrollment_token_file(), mark_device_enrolled(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), generate_token()

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (20): DiskInfo, MediaType, Model, SizeBytes, MonitorInfo, Height, Manufacturer, Name (+12 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (19): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.19
Nodes (3): admin_device_config(), get_device(), list_devices()

### Community 23 - "Community 23"
Cohesion: 0.10
Nodes (20): HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate, BiosVersion, Cpu, Disks, Gpus (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (12): AgentApiException, IsAuthFailure, OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (11): enroll(), inventory(), rotate_device_key(), admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), api_key_lookup() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (9): delete_msi_version(), ingest_uploaded_msi(), prune_old_msi_versions(), sync_from_github(), version_from_msi_name(), versions_pinned_in_config(), admin_agent_update_sync(), admin_agent_update_upload() (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (10): authenticate_web_user(), current_web_user(), require_web_admin(), dump_session(), load_session(), WebUser, login_submit(), password_submit() (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.20
Nodes (8): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename()

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (6): effective_settings_for_device(), effective_update_target_for_device(), ops_update_signals(), resolve_target_msi(), set_latest_msi_version(), agent_update_msi()

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (5): check_update(), is_newer(), parse_semver(), _semver_equal(), sort_key()

### Community 32 - "Community 32"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.24
Nodes (6): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), set_csrf_cookie(), validate_csrf()

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.22
Nodes (8): _apply_bool_form_fields(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policy_create(), policy_update(), _settings_raw_from_form(), _validate_update_target_pin()

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 42 - "Community 42"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.36
Nodes (6): _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test(), LdapFormData, _parse_ldap_form()

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (3): admin_agent_update_delete(), admin_delete_device_override(), delete_device()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 57 - "Community 57"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 58 - "Community 58"
Cohesion: 0.33
Nodes (3): _device_inventory_nav(), _format_bytes(), _format_os()

### Community 59 - "Community 59"
Cohesion: 0.40
Nodes (4): CpuInfo, Cores, Logical, Name

## Knowledge Gaps
- **185 isolated node(s):** `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+180 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 401 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 13` to `Community 24`, `Community 17`, `Community 4`?**
  _High betweenness centrality (0.301) - this node is a cross-community bridge._
- **Are the 112 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 112 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentLocalKeys`, `ApiKey`, `CollectHardware` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05333333333333334 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 6` to `Community 0`, `Community 2`, `Community 3`, `Community 7`, `Community 8`, `Community 9`, `Community 39`, `Community 11`, `Community 46`, `Community 15`, `Community 16`, `Community 51`, `Community 21`, `Community 25`, `Community 26`, `Community 27`, `Community 29`, `Community 31`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05886708626434654 - nodes in this community are weakly interconnected._