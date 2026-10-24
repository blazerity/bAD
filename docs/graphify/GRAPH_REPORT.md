# Graph Report - workspace  (2026-10-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1802 nodes · 5130 edges · 95 communities (66 shown, 29 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 593 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `991830c0`
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

## God Nodes (most connected - your core abstractions)
1. `Database` - 246 edges
2. `Settings` - 117 edges
3. `WebUser` - 88 edges
4. `InventoryCollector` - 64 edges
5. `post()` - 59 edges
6. `AgentConfig` - 56 edges
7. `_html()` - 52 edges
8. `HardwareInfo` - 43 edges
9. `utc_now()` - 41 edges
10. `InventorySnapshot` - 30 edges

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

## Communities (95 total, 29 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (40): admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token() (+32 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (6): seed_default_admin(), try_local_login(), Database, utc_now(), mark_device_enrolled(), _finalize_digest_send()

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (42): Settings, releases_dir(), read_domain_from_env(), backups_settings_run(), device_config_override_save(), device_merge(), _device_merge_page(), device_revoke() (+34 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (34): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_delete_device_override() (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (22): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z() (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (25): device_silence_status(), effective_stale_after_seconds(), health_snippet(), parse_site_stale_seconds(), parse_utc(), meta_facet_matches(), normalize_wave_filter(), _attach_duplicate_signals() (+17 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (17): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (25): current_web_user(), require_web_admin(), dump_session(), load_session(), WebUser, event_visual(), https_panel_url(), _backup_context() (+17 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (4): InventoryCollector, MsftPhysicalDiskRow, Serial, UniqueId

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (24): enrollment_rotation_signals(), enrollment_status(), _accumulate_hw_bars(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner(), build_dashboard_stats() (+16 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (23): get_session_secret(), encrypt_secret(), cookie_secure_for_request(), set_csrf_cookie(), client_ip(), parse_recipients(), _apply_bool_form_fields(), _build_enrollment_msiexec_script() (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (32): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, CpuInfo, Cores (+24 more)

### Community 16 - "Community 16"
Cohesion: 0.15
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (16): event_importance(), sensitive_over_http_blocked(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active(), https_first_status(), merge_security_into_ops(), _secret_source() (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (16): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), flush_inventory_mail_digest() (+8 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (11): AntivirusProductInfo, Name, ProductState, CollectorError, Error, Section, SecurityInfo, Antivirus (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (3): DeviceIdentity, WmiHelper, BadAgent

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (26): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (16): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle() (+8 more)

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (3): AgentUpdater, UpdatePathUtil, VersionUtil

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.16
Nodes (15): enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), _amd_family(), cpu_family_label(), cpu_vendor_label(), disk_bucket_from_fixed_bytes(), disk_role() (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (6): delete_msi_version(), prune_old_msi_versions(), set_latest_msi_version(), versions_pinned_in_config(), agent_update_msi(), _enrollment_msi_name()

### Community 30 - "Community 30"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (11): ingest_uploaded_msi(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.25
Nodes (16): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key() (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (11): admin_token_valid(), get_data_key(), get_db(), require_admin_token(), require_api_key(), require_enrollment_token(), require_web_user(), api_key_lookup() (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (8): heartbeat(), inventory(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), set_device_refresh_request(), mark_uninstall_sent_patch()

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (13): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), _parse_utc_iso(), request_device_uninstall() (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (9): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, InventoryRequest (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.16
Nodes (11): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), resolve_target_cached(), parse_semver() (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.16
Nodes (14): device_panel_href(), device_search_meta_line(), event_match_label(), resolve_device_ref(), device_archive(), device_delete(), device_request_refresh(), device_restore() (+6 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (10): enroll(), rotate_device_key(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file() (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (10): authenticate_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+2 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (4): SlidingWindowRateLimiter, build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (4): adapt_sql(), CompatConnection, connect_postgres(), _split_sql_statements()

### Community 52 - "Community 52"
Cohesion: 0.15
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (5): generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 61 - "Community 61"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.40
Nodes (4): generate_bad_id(), is_bad_id(), apply_user_presence_patch(), run_wave_21_migration()

### Community 66 - "Community 66"
Cohesion: 0.31
Nodes (5): format_logged_on_display(), meta_search_haystack(), normalize_logged_on_list(), device_match_label(), highlight_match()

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 68 - "Community 68"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 69 - "Community 69"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 70 - "Community 70"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 73 - "Community 73"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 75 - "Community 75"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 77 - "Community 77"
Cohesion: 0.67
Nodes (5): init(), parseJson(), renderGauges(), renderSparkline(), renderTreemap()

### Community 78 - "Community 78"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 79 - "Community 79"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 84 - "Community 84"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **216 isolated node(s):** `Serial`, `UniqueId`, `ChargePercent`, `EstimatedRuntimeMinutes`, `Name` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 561 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 19` to `Community 64`, `Community 5`, `Community 48`, `Community 22`, `Community 58`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Are the 137 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 137 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Serial`, `UniqueId`, `ChargePercent` to the rest of the system?**
  _216 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.1005464480874317 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 1` to `Community 2`, `Community 3`, `Community 6`, `Community 9`, `Community 10`, `Community 11`, `Community 13`, `Community 14`, `Community 17`, `Community 18`, `Community 24`, `Community 29`, `Community 31`, `Community 33`, `Community 35`, `Community 36`, `Community 40`, `Community 41`, `Community 43`, `Community 46`, `Community 51`, `Community 62`, `Community 69`, `Community 76`, `Community 86`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 102 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07142857142857142 - nodes in this community are weakly interconnected._