# Graph Report - workspace  (2026-11-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1911 nodes · 5441 edges · 98 communities (66 shown, 32 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 613 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8f3e273d`
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
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 93
- Community 94
- Community 96

## God Nodes (most connected - your core abstractions)
1. `Database` - 254 edges
2. `Settings` - 117 edges
3. `WebUser` - 88 edges
4. `InventoryCollector` - 64 edges
5. `post()` - 59 edges
6. `AgentConfig` - 56 edges
7. `_html()` - 52 edges
8. `HardwareInfo` - 43 edges
9. `utc_now()` - 41 edges
10. `BadAgent` - 32 edges

## Surprising Connections (you probably didn't know these)
- `check_update()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_settings_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_update_target_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `ingest_uploaded_msi()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `ops_update_signals()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py

## Import Cycles
- None detected.

## Communities (98 total, 32 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (15): delete_msi_version(), versions_pinned_in_config(), admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), delete_device(), get_device(), list_devices() (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (81): device_panel_href(), set_csrf_cookie(), parse_site_stale_seconds(), dump_session(), WebUser, event_visual(), resolve_device_ref(), backups_settings_page() (+73 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (58): admin_agent_config_defaults(), admin_server_update_apply_status(), admin_server_update_branches(), admin_server_update_check(), admin_server_update_msi_trigger(), _admin_server_update_request(), admin_server_update_rollback(), admin_server_update_set_branch() (+50 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (42): admin_enrollment_rotate(), admin_security_status(), Settings, effective_stale_after_seconds(), enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_device_enrolled() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (25): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (9): InventoryCollector, CollectorError, Error, Section, SecurityInfo, Antivirus, SecureBoot, TpmPresent (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (25): _accumulate_hw_bars(), aggregate_incident_feed(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner(), build_dashboard_stats(), _hbar_block() (+17 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (29): format_logged_on_display(), normalize_logged_on_user(), disk_role(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label() (+21 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (21): prune_old_msi_versions(), set_latest_msi_version(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config() (+13 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (4): AgentUpdater, UpdateCli, UpdatePathUtil, VersionUtil

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (30): CpuInfo, Cores, Logical, Name, HardwareInfo, BaseboardSerial, Battery, BiosManufacturer (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (19): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value() (+11 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (27): AntivirusProductInfo, Name, ProductState, DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId (+19 more)

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (14): ingest_uploaded_msi(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+6 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (15): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (15): generate_bad_id(), is_bad_id(), connect_postgres(), apply_user_presence_patch(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (21): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (18): default_digest_weekdays(), digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours(), dump_notify_flags(), filter_events_for_mail(), _finalize_digest_send(), flush_inventory_mail_digest() (+10 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (4): AgentUninstaller, MsiexecLauncher, UninstallCli, WindowsEventLog

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 28 - "Community 28"
Cohesion: 0.23
Nodes (14): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.16
Nodes (13): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), format_cpu_short(), _intel_core_i_family(), _intel_family(), meta_facet_matches() (+5 more)

### Community 30 - "Community 30"
Cohesion: 0.18
Nodes (12): admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token(), require_web_user() (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (12): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), resolve_target_cached(), parse_semver() (+4 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (12): collect_hardware_serials(), enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), disk_bucket_from_fixed_bytes(), format_ram_ddr(), format_ram_gib(), format_ram_list_cell() (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (11): _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line(), event_match_label(), matched_serial_subtitle() (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (3): adapt_sql(), CompatConnection, _split_sql_statements()

### Community 39 - "Community 39"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.17
Nodes (7): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _dispatch(), _polarity_marker_html(), send_email()

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (9): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), ldap_settings_save(), ldap_settings_test(), LdapFormData (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (11): highlight_match(), _chassis_map_for_devices(), _chassis_type_from_device(), _device_config_context(), devices_search_json(), _duplicate_groups(), _format_chassis(), _normalize_chassis_type() (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.23
Nodes (7): enroll(), inventory(), rotate_device_key(), client_ip(), generate_token(), hash_secret(), device_rotate_key()

### Community 52 - "Community 52"
Cohesion: 0.18
Nodes (7): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId

### Community 54 - "Community 54"
Cohesion: 0.31
Nodes (5): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 57 - "Community 57"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.28
Nodes (6): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key(), generate_session_secret()

### Community 62 - "Community 62"
Cohesion: 0.36
Nodes (4): device_silence_status(), parse_utc(), _device_freshness_tier(), _enrich_device_row()

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 64 - "Community 64"
Cohesion: 0.39
Nodes (3): decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 66 - "Community 66"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 67 - "Community 67"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 69 - "Community 69"
Cohesion: 0.43
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 70 - "Community 70"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 72 - "Community 72"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 74 - "Community 74"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 75 - "Community 75"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 76 - "Community 76"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 79 - "Community 79"
Cohesion: 0.40
Nodes (3): _stale_pass(), notify_device_back_online(), notify_stale_device()

### Community 81 - "Community 81"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **216 isolated node(s):** `Cores`, `Logical`, `Name`, `BaseboardSerial`, `Battery` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 591 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 38`, `Community 11`, `Community 12`, `Community 45`, `Community 46`, `Community 15`, `Community 19`, `Community 51`, `Community 22`, `Community 62`, `Community 25`, `Community 28`, `Community 61`, `Community 30`, `Community 31`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 141 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 141 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Cores`, `Logical`, `Name` to the rest of the system?**
  _216 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.04438224710115954 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 18` to `Community 40`, `Community 13`, `Community 21`, `Community 26`, `Community 60`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Are the 102 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06796116504854369 - nodes in this community are weakly interconnected._