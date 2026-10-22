# Graph Report - bAD  (2026-10-22)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1442 nodes · 4153 edges · 82 communities (62 shown, 20 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 496 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6b6ce9bf`
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
- Community 49
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
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 77
- Community 81

## God Nodes (most connected - your core abstractions)
1. `Database` - 213 edges
2. `Settings` - 111 edges
3. `WebUser` - 82 edges
4. `AgentConfig` - 55 edges
5. `_html()` - 49 edges
6. `HardwareInfo` - 42 edges
7. `InventoryCollector` - 40 edges
8. `utc_now()` - 33 edges
9. `InventorySnapshot` - 30 edges
10. `ConfigCli` - 28 edges

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

## Communities (82 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (39): _admin_server_update_request(), admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+31 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (4): list_events(), Database, utc_now(), mark_device_enrolled()

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (24): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (7): UpdateAction, Downgrade, None, Upgrade, DeviceIdentity, WmiHelper, BadAgent

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (30): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy() (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (6): AsciiReportWriter, BadCli, HtmlReportWriter, IInventoryCollector, ReportFormat, ReportPathResolver

### Community 6 - "Community 6"
Cohesion: 0.19
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (21): set_csrf_cookie(), normalize_wave_filter(), _attach_duplicate_signals(), _build_enrollment_msiexec_script(), _device_inventory_nav(), _disk_overview_line(), devices_csv_export(), devices_page() (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (26): require_web_admin(), WebUser, device_archive(), device_delete(), device_merge(), device_restore(), events_page(), password_page() (+18 more)

### Community 11 - "Community 11"
Cohesion: 0.14
Nodes (13): ingest_uploaded_msi(), prune_old_msi_versions(), sync_from_github(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset() (+5 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (28): DiskInfo, InterfaceType, MediaType, Model, SerialNumber, SizeBytes, HardwareInfo, BaseboardSerial (+20 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (18): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (5): adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), _split_sql_statements()

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (15): admin_token_valid(), current_web_user(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token() (+7 more)

### Community 17 - "Community 17"
Cohesion: 0.10
Nodes (7): delete_msi_version(), ops_update_signals(), set_latest_msi_version(), versions_pinned_in_config(), admin_agent_update_status(), agent_update_msi(), _enrollment_msi_name()

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (13): compute_setting_sources(), build_attention_queue(), build_bootstrap_checklist(), build_config_winner(), build_dashboard_stats(), build_wave_counts(), device_has_agent_local(), _facet_from_device_meta() (+5 more)

### Community 20 - "Community 20"
Cohesion: 0.13
Nodes (10): effective_stale_after_seconds(), sensitive_over_http_blocked(), https_first_status(), merge_security_into_ops(), _secret_source(), secrets_status(), security_status(), dashboard_page() (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.19
Nodes (3): AgentUpdater, UpdatePlan, VersionUtil

### Community 22 - "Community 22"
Cohesion: 0.09
Nodes (22): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, CpuInfo, Cores (+14 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (16): Settings, _device_config_context(), device_detail_page(), _device_merge_page(), device_revoke(), device_rotate_key(), device_tags_save(), enrollment_rotate() (+8 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (11): compute_effective_config(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches(), provenance_from_effective() (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (13): AgentApiException, IsAuthFailure, OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.29
Nodes (15): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _minidump_files_by_name() (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (12): RemoteAgentConfigResponse, Settings, Version, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId (+4 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (9): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, InventoryRequest (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.27
Nodes (10): _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin(), get_settings() (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.16
Nodes (10): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), resolve_target_cached(), parse_semver(), resolve_target_msi() (+2 more)

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (12): authenticate_web_user(), load_ldap_view(), try_ldap_login(), encrypt_secret(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+4 more)

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (9): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file() (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.23
Nodes (4): ConfigStore, ConfigPath, LogsDir, ProgramDataDir

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (15): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.16
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (11): _apply_bool_form_fields(), device_config_override_save(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policies_page(), policy_create(), policy_edit_page() (+3 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (10): _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), devices_search_json(), home(), overview_alias() (+2 more)

### Community 46 - "Community 46"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 47 - "Community 47"
Cohesion: 0.24
Nodes (4): device_silence_status(), health_snippet(), normalize_tags(), parse_utc()

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (5): generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 53 - "Community 53"
Cohesion: 0.20
Nodes (10): RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion, HeartbeatIntervalMinutes, InventoryIntervalHours, UpdateCheckIntervalHours (+2 more)

### Community 55 - "Community 55"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (4): admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 58 - "Community 58"
Cohesion: 0.22
Nodes (5): cookie_secure_for_request(), dump_session(), _clear_session_cookie(), logout(), _set_session_cookie()

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (3): enroll(), inventory(), rotate_device_key()

### Community 60 - "Community 60"
Cohesion: 0.25
Nodes (8): AntivirusProductInfo, Name, ProductState, SecurityInfo, Antivirus, SecureBoot, TpmPresent, TpmSpecVersion

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 63 - "Community 63"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 66 - "Community 66"
Cohesion: 0.43
Nodes (4): event_importance(), event_passes_importance(), importance_rank(), types_at_least()

### Community 67 - "Community 67"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (5): parse_site_stale_seconds(), _invalidate_fleet_snapshot_cache(), _retention_context(), retention_settings_page(), retention_settings_save()

### Community 70 - "Community 70"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 71 - "Community 71"
Cohesion: 0.40
Nodes (4): ConfigLocalPayload, Keys, ServerUrl, Settings

### Community 72 - "Community 72"
Cohesion: 0.60
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 75 - "Community 75"
Cohesion: 0.83
Nodes (3): apply(), formatLocal(), pad2()

## Knowledge Gaps
- **206 isolated node(s):** `InterfaceType`, `MediaType`, `Model`, `SerialNumber`, `SizeBytes` (+201 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 463 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 1` to `Community 4`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 15`, `Community 16`, `Community 17`, `Community 20`, `Community 23`, `Community 34`, `Community 35`, `Community 36`, `Community 37`, `Community 44`, `Community 45`, `Community 47`, `Community 57`, `Community 59`, `Community 63`, `Community 69`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Are the 122 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 122 INFERRED edges - model-reasoned connections that need verification._
- **What connects `InterfaceType`, `MediaType`, `Model` to the rest of the system?**
  _206 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.11753246753246753 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 18` to `Community 21`, `Community 3`, `Community 28`, `Community 5`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08244897959183674 - nodes in this community are weakly interconnected._