# Graph Report - workspace  (2026-11-03)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1994 nodes · 5718 edges · 102 communities (68 shown, 34 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 468 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dddd5283`
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
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 100

## God Nodes (most connected - your core abstractions)
1. `Database` - 279 edges
2. `WebUser` - 92 edges
3. `Settings` - 71 edges
4. `InventoryCollector` - 64 edges
5. `post()` - 64 edges
6. `AgentConfig` - 56 edges
7. `_html()` - 53 edges
8. `utc_now()` - 45 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 33 edges

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

## Communities (102 total, 34 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (8): admin_create_policy(), revoke_device(), try_local_login(), Database, _enrollment_msi_name(), events_page(), password_submit(), render()

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (56): cookie_secure_for_request(), WebUser, _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), dashboard_page() (+48 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (41): require_web_admin(), set_csrf_cookie(), sensitive_over_http_blocked(), list_integrations(), revoke(), highlight_match(), default_digest_weekdays(), parse_recipients() (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (39): delete_msi_version(), admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_delete_device_override() (+31 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (53): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+45 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (30): device_silence_status(), health_snippet(), parse_utc(), importance_rank(), types_at_least(), normalize_os_caption(), _accumulate_hw_bars(), aggregate_incident_feed() (+22 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (39): admin_server_update_set_token(), utc_now(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+31 more)

### Community 7 - "Community 7"
Cohesion: 0.14
Nodes (9): InventoryCollector, CollectorError, Error, Section, SecurityInfo, Antivirus, SecureBoot, TpmPresent (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (27): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _device_card_html(), digest_schedule_preview_ru(), digest_send_due() (+19 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (22): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z() (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (14): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_device_enrolled(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), panel_tls_mode() (+6 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (22): effective_stale_after_seconds(), parse_site_stale_seconds(), event_importance(), build_bootstrap_checklist(), build_bootstrap_progress(), normalize_wave_filter(), patch_security_for_qa(), merge_security_into_ops() (+14 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (5): AgentApiException, IsAuthFailure, BadApiClient, WindowsEventLog, Worker

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (17): ingest_uploaded_msi(), is_newer(), parse_semver(), prune_old_msi_versions(), _semver_equal(), sync_from_github(), version_from_msi_name(), sort_key() (+9 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (18): _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+10 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (22): enrich_hardware_meta(), _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_bucket_from_fixed_bytes(), disk_role(), format_cpu_short() (+14 more)

### Community 20 - "Community 20"
Cohesion: 0.09
Nodes (4): AssemblyProbe, DeviceIdentity, WmiHelper, BadAgent

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (19): create_integration_request(), enroll(), _integration_http_error(), poll_integration_request(), rotate_device_key(), rotate_enrollment_token(), client_ip(), approve() (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.14
Nodes (17): apply_user_presence_patch(), collect_hardware_serials(), _add(), format_logged_on_display(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type(), normalize_logged_on_list() (+9 more)

### Community 25 - "Community 25"
Cohesion: 0.14
Nodes (3): AgentUpdater, UpdatePathUtil, VersionUtil

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (13): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), sort_ipv4_addresses(), set_lock_timeout(), _assign_bad_ids(), _backfill_bad_ids(), _backfill_device_meta() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (14): admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token(), require_web_user() (+6 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (15): UpdateAction, Downgrade, None, Upgrade, UpdateCheckResponse, Action, Desired, MsiName (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.24
Nodes (20): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _format_free_gib() (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (4): HardwareMaps, MsftPhysicalDiskRow, Serial, UniqueId

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.12
Nodes (10): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ops_update_signals(), resolve_target_cached(), resolve_target_msi(), set_latest_msi_version() (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.16
Nodes (11): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, IntegrationLookupBody (+3 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (8): CompatConnection, connect_postgres(), _split_sql_statements(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes(), index_exists()

### Community 38 - "Community 38"
Cohesion: 0.22
Nodes (13): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), _parse_utc_iso(), request_device_uninstall() (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (17): archive_device(), request_device_refresh_api(), restore_device(), device_panel_href(), set_device_refresh_request(), resolve_device_ref(), device_archive(), _device_config_context() (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.18
Nodes (3): AgentUninstaller, MsiexecLauncher, UninstallCli

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 44 - "Community 44"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (10): authenticate_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+2 more)

### Community 49 - "Community 49"
Cohesion: 0.19
Nodes (6): build_server_runtime(), _probe_database(), _process_memory_bytes(), _cpu_for(), main(), seed_one()

### Community 50 - "Community 50"
Cohesion: 0.14
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 57 - "Community 57"
Cohesion: 0.29
Nodes (5): generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 58 - "Community 58"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 61 - "Community 61"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (6): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), mark_uninstall_sent_patch()

### Community 65 - "Community 65"
Cohesion: 0.25
Nodes (3): current_web_user(), dump_session(), load_session()

### Community 66 - "Community 66"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 68 - "Community 68"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 70 - "Community 70"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 71 - "Community 71"
Cohesion: 0.43
Nodes (3): decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 73 - "Community 73"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 74 - "Community 74"
Cohesion: 0.33
Nodes (4): _device_inventory_nav(), _disk_overview_line(), _format_bytes(), _format_os()

### Community 76 - "Community 76"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 78 - "Community 78"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 79 - "Community 79"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 83 - "Community 83"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **216 isolated node(s):** `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 617 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 8`, `Community 13`, `Community 14`, `Community 16`, `Community 17`, `Community 18`, `Community 22`, `Community 23`, `Community 26`, `Community 27`, `Community 32`, `Community 37`, `Community 38`, `Community 39`, `Community 47`, `Community 62`, `Community 65`, `Community 68`, `Community 69`, `Community 77`, `Community 91`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 99 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentLocalKeys`, `ApiKey`, `CollectHardware` to the rest of the system?**
  _216 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05176116838487973 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 15` to `Community 64`, `Community 43`, `Community 20`, `Community 54`, `Community 25`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `require_web_admin()`) actually correct?**
  _`WebUser` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.10699062233589088 - nodes in this community are weakly interconnected._