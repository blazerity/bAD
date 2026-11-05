# Graph Report - bAD-simplify-d100  (2026-11-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2109 nodes · 6068 edges · 107 communities (75 shown, 32 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 703 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `feda0654`
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
- Community 86
- Community 87
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 100
- Community 101
- Community 105

## God Nodes (most connected - your core abstractions)
1. `Database` - 296 edges
2. `Settings` - 123 edges
3. `WebUser` - 95 edges
4. `post()` - 70 edges
5. `InventoryCollector` - 64 edges
6. `AgentConfig` - 60 edges
7. `_html()` - 54 edges
8. `utc_now()` - 48 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 35 edges

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

## Communities (107 total, 32 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (14): delete_msi_version(), prune_old_msi_versions(), versions_pinned_in_config(), admin_agent_update_sync(), admin_agent_update_upload(), issue_agent_signing_key(), try_local_login(), Database (+6 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (89): current_web_user(), load_ldap_view(), Settings, cookie_secure_for_request(), set_csrf_cookie(), sensitive_over_http_blocked(), dump_session(), load_session() (+81 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (43): admin_server_update_set_branch(), admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+35 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (41): set_latest_msi_version(), admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy() (+33 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (31): device_silence_status(), health_snippet(), parse_utc(), importance_rank(), types_at_least(), _accumulate_hw_bars(), aggregate_incident_feed(), build_attention_queue() (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (31): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+23 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (24): require_web_admin(), effective_stale_after_seconds(), parse_site_stale_seconds(), event_importance(), normalize_wave_filter(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active() (+16 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (22): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z() (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (17): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (23): enroll(), admin_token_valid(), ensure_bootstrap_secrets(), _persist(), get_data_key(), get_db(), get_session_secret(), _read_secret_file() (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (32): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+24 more)

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (14): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file() (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (4): AgentUpdater, MsiexecLauncher, UpdatePathUtil, VersionUtil

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (17): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals(), resolve_target_cached() (+9 more)

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (25): device_panel_href(), set_device_refresh_request(), resolve_device_ref(), _apply_bool_form_fields(), _chassis_map_for_devices(), _chassis_type_from_device(), device_archive(), _device_config_context() (+17 more)

### Community 19 - "Community 19"
Cohesion: 0.16
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (22): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _format_free_gib() (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (3): SigningKeyFetchResult, DeviceIdentity, BadAgent

### Community 22 - "Community 22"
Cohesion: 0.08
Nodes (21): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+13 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (15): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _device_card_html(), _dispatch(), _event_row_html() (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (18): rotate_device_key(), decrypt_secret(), encrypt_secret(), _fernet_from_key(), approve(), _clean_name(), create_request(), IntegrationError (+10 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (18): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_bucket_from_fixed_bytes(), disk_role(), format_cpu_short(), _intel_core_i_family() (+10 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (26): HardwareInfo, BaseboardSerial, Battery, BiosManufacturer, BiosReleaseDate, BiosSerial, BiosVersion, ChassisType (+18 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (21): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+13 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (14): _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval(), _smtp_password() (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (3): EnrollmentHints, EnrollmentRequestResult, WmiHelper

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (14): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody, EnrollRequest (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (13): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), sort_ipv4_addresses(), set_lock_timeout(), _assign_bad_ids(), _backfill_bad_ids(), _backfill_device_meta() (+5 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.16
Nodes (8): CompatConnection, connect_postgres(), _split_sql_statements(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes(), index_exists()

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (3): AgentUninstaller, UninstallCli, WindowsEventLog

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (11): create_app(), _device_id(), _snap_count(), test_enrollment_request_waits_for_admin(), test_fat_inventory_does_not_write(), test_inventory_signature_uses_agent_canon(), test_old_agent_shared_token_without_signature(), test_one_time_code_burns() (+3 more)

### Community 38 - "Community 38"
Cohesion: 0.21
Nodes (13): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), _parse_utc_iso(), request_device_uninstall() (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.15
Nodes (16): default_digest_weekdays(), digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours(), dump_notify_flags(), filter_events_for_mail(), flush_inventory_mail_digest(), flush_mail_digest() (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.17
Nodes (3): HardwareMaps, MinidumpBugcheck, Result

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (3): PushCli, ServerUrlRules, UpdateCli

### Community 42 - "Community 42"
Cohesion: 0.19
Nodes (12): apply_user_presence_patch(), enrich_hardware_meta(), format_logged_on_display(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type(), normalize_logged_on_list(), normalize_logged_on_user() (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.16
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (11): collect_hardware_serials(), _add(), normalize_search_serial(), device_match_label(), device_search_meta_line(), event_match_label(), highlight_match(), matched_serial_subtitle() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 47 - "Community 47"
Cohesion: 0.14
Nodes (7): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.18
Nodes (3): AgentSigningKey, KeyPath, SkipFetchPath

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.16
Nodes (8): create_integration_request(), _enforce_enroll_rate(), _enrollment_request_id(), _integration_http_error(), inventory(), poll_integration_request(), submit_enrollment_request(), client_ip()

### Community 55 - "Community 55"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (4): SlidingWindowRateLimiter, build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 57 - "Community 57"
Cohesion: 0.27
Nodes (7): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json()

### Community 58 - "Community 58"
Cohesion: 0.26
Nodes (8): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), _parse_utc_iso(), refresh_request_pending(), _utc_iso_ge(), mark_uninstall_sent_patch()

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 62 - "Community 62"
Cohesion: 0.24
Nodes (5): create_enrollment_grant(), enrollment_code_hash(), inventory_signing_bytes(), new_device_signing_key(), verify_inventory_signature()

### Community 63 - "Community 63"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 65 - "Community 65"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.56
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 69 - "Community 69"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 72 - "Community 72"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 73 - "Community 73"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 74 - "Community 74"
Cohesion: 0.43
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 75 - "Community 75"
Cohesion: 0.33
Nodes (4): _device_inventory_nav(), _disk_overview_line(), _format_bytes(), _format_os()

### Community 76 - "Community 76"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 77 - "Community 77"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 80 - "Community 80"
Cohesion: 0.60
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 81 - "Community 81"
Cohesion: 0.40
Nodes (3): _stale_pass(), notify_device_back_online(), notify_stale_device()

### Community 83 - "Community 83"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **221 isolated node(s):** `bad-server`, `IsAuthFailure`, `Name`, `ProductState`, `ChargePercent` (+216 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 646 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 13` to `Community 67`, `Community 7`, `Community 41`, `Community 45`, `Community 16`, `Community 21`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Are the 173 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 173 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `IsAuthFailure`, `Name` to the rest of the system?**
  _221 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.037718396711202466 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 9`, `Community 11`, `Community 12`, `Community 15`, `Community 17`, `Community 18`, `Community 23`, `Community 24`, `Community 28`, `Community 33`, `Community 35`, `Community 38`, `Community 48`, `Community 54`, `Community 58`, `Community 62`, `Community 87`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 107 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 107 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06380857427716849 - nodes in this community are weakly interconnected._