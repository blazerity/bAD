# Graph Report - bAD  (2026-11-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2414 nodes · 7039 edges · 118 communities (83 shown, 35 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 776 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3a5601ec`
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
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 100
- Community 101
- Community 102
- Community 103
- Community 105
- Community 106
- Community 107
- Community 115

## God Nodes (most connected - your core abstractions)
1. `Database` - 306 edges
2. `Settings` - 125 edges
3. `WebUser` - 101 edges
4. `post()` - 71 edges
5. `AgentConfig` - 69 edges
6. `InventoryCollector` - 65 edges
7. `_html()` - 55 edges
8. `utc_now()` - 51 edges
9. `BadAgent` - 46 edges
10. `diff_inventory_snapshots()` - 44 edges

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

## Communities (118 total, 35 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (49): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename() (+41 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (9): BadCli, CliColumns, IInventoryCollector, PushCli, ServiceChannel, ServiceCli, UninstallCli, UpdateCli (+1 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (9): seed_default_admin(), _compact_json(), Database, utc_now(), mark_device_enrolled(), types_exact_importance(), record_use(), _finalize_digest_send() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (42): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_create_policy(), admin_delete_policy(), admin_device_config() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (26): AgentConfig, AgentLocalKeys, ApiKey, BadId, CollectHardware, CollectSoftware, CollectUsers, EnrollmentCode (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (32): get_session_secret(), default_digest_weekdays(), dump_notify_flags(), parse_recipients(), https_panel_url(), read_domain_from_env(), _apply_bool_form_fields(), _apply_inventory_overlay() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (35): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+27 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (43): admin_server_update_set_branch(), Settings, releases_dir(), WebUser, _archive_device(), _clear_session_cookie(), device_archive(), device_delete() (+35 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (39): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bag_delta(), _bios_token(), _both_lists(), _bugcheck_code() (+31 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (11): CliLine, CliOutcome, ExitCode, Html, KeyRejected, Lines, StopAfterReply, Tail (+3 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (19): sanitize_update_target(), check_update(), delete_msi_version(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals() (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (23): OfflineFlushResult, AuthException, AuthFailed, BoardChanged, Deferred, Error, Failures, NextRetryUtc (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (23): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (35): backup_keys_status(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), _chassis_map_for_devices(), _chassis_type_from_device() (+27 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (6): AgentApiException, IsAuthFailure, IsBoardChanged, BadApiClient, EnrollResult, InventoryPostFailure

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (19): effective_stale_after_seconds(), sensitive_over_http_blocked(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active(), https_first_status(), merge_security_into_ops(), _secret_source() (+11 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (31): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatActions, Inventory, Uninstall, UpdateCheck (+23 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (9): AgentUpdater, UpdateAction, Downgrade, None, Upgrade, UpdatePlan, MsiexecLauncher, UpdatePathUtil (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.08
Nodes (15): AgentSigningKey, KeyPath, SkipFetchPath, InventorySignTrace, UpdateCheckResponse, Action, Desired, MsiName (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (34): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+26 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (19): admin_enrollment_rotate(), create_enrollment_grant(), _display_serial(), _enforce_enroll_rate(), enroll(), issue_agent_signing_key(), rotate_device_key(), submit_enrollment_request() (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.06
Nodes (32): CpuInfo, Cores, Logical, Name, GpuInfo, AdapterRamBytes, DriverVersion, Name (+24 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (16): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (21): enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_bucket_from_fixed_bytes() (+13 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (15): backup_filename(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup(), run_pg_dump() (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.15
Nodes (5): InvalidKeyReset, LinkProbe, LinkProbeStatus, ReportRelay, Worker

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (17): badge_recent_after_seconds(), effective_recent_after_seconds(), stale_days_form(), _device_freshness_tier(), _freshness_limits(), _invalidate_fleet_snapshot_cache(), _retention_context(), retention_settings_save() (+9 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (18): build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner(), build_dashboard_stats(), _hbar_block(), build_wave_counts(), chart_filter_href() (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (4): DeviceIdentity, QuietFiles, TextLimit, BadAgent

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (9): adapt_sql(), CompatConnection, connect_postgres(), _split_sql_statements(), connect_autocommit(), create_index_concurrently(), ensure_trgm_search_indexes(), index_exists() (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.12
Nodes (12): load_ldap_view(), try_ldap_login(), authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn() (+4 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (18): create_integration_request(), _integration_http_error(), poll_integration_request(), approve(), _clean_name(), create_request(), integration_from_token(), IntegrationError (+10 more)

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (14): admin_token_valid(), authenticate_web_user(), get_data_key(), get_db(), require_admin_token(), require_api_key(), require_web_user(), try_local_login() (+6 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (15): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody, EnrollRequest (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.16
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 38 - "Community 38"
Cohesion: 0.20
Nodes (21): create_app(), encrypt_secret(), dump_name_ok(), _bad_id(), _device_row(), _fingerprint(), _snap_count(), test_agent_report_html_is_enrolled_card_without_admin() (+13 more)

### Community 39 - "Community 39"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 40 - "Community 40"
Cohesion: 0.10
Nodes (18): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, BadId, CollectedAt (+10 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (10): parse_iso(), parse_site_recent_seconds(), parse_site_stale_seconds(), parse_utc(), retention_threshold_seconds(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch() (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.19
Nodes (5): MinidumpBugcheck, Result, MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (13): apply_user_presence_patch(), collect_hardware_serials(), _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line() (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (12): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), request_device_uninstall(), start_new_uninstall_request_patch() (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 48 - "Community 48"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (9): _log_inventory_signature(), ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), _fernet_from_key(), generate_data_key() (+1 more)

### Community 50 - "Community 50"
Cohesion: 0.20
Nodes (10): agent_minidump(), _copy_minidump(), cause_label(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header() (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.18
Nodes (7): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (15): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+7 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (4): admin_delete_device_override(), heartbeat(), set_device_refresh_request(), mark_uninstall_sent_patch()

### Community 56 - "Community 56"
Cohesion: 0.15
Nodes (12): require_web_admin(), normalize_wave_filter(), _attach_duplicate_signals(), _auth_is_api(), _contact_is_after_enroll(), devices_csv_export(), _devices_filter_chips(), _qs() (+4 more)

### Community 57 - "Community 57"
Cohesion: 0.35
Nodes (13): _csrf(), _fp(), _hashes(), _login(), _request(), test_allow_any_bad_id_issues_key(), test_allow_empty_device_creates_card_and_flash_is_once(), test_allow_live_card_rotates_key() (+5 more)

### Community 58 - "Community 58"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (3): highlight_match(), devices_search_json(), overview_search_json()

### Community 61 - "Community 61"
Cohesion: 0.44
Nodes (13): _allow(), _claim(), _device_count(), _fp(), _login(), _request(), _snaps(), test_bad_id_required() (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (7): _accept_policy(), _filter_policy_settings(), _policies_context(), policy_create(), policy_update(), PolicyFormData, _validate_update_target_pin()

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (5): EnrollmentHints, UsersInfo, LastInteractive, LoggedOn, WmiHelper

### Community 65 - "Community 65"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.18
Nodes (3): SigningKeyFetchResult, EnrollmentProof, ProofPath

### Community 67 - "Community 67"
Cohesion: 0.35
Nodes (9): get_settings(), _bad_id(), _enroll(), _html(), _panel(), test_card_without_snapshot_keeps_empty_sections(), test_gpu_panel_unchanged_when_present(), test_report_does_not_keep_empty_sections() (+1 more)

### Community 69 - "Community 69"
Cohesion: 0.19
Nodes (7): current_web_user(), dump_flash(), dump_session(), load_flash(), load_session(), _session_secret(), _take_flash()

### Community 70 - "Community 70"
Cohesion: 0.24
Nodes (6): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), set_csrf_cookie(), validate_csrf()

### Community 71 - "Community 71"
Cohesion: 0.18
Nodes (9): format_logged_on_display(), _device_inventory_nav(), _disk_overview_line(), _enrich_device_row(), _format_bytes(), _format_chassis(), _format_os(), _pending_reboot_visible() (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.24
Nodes (3): MsftPhysicalDiskRow, Serial, UniqueId

### Community 73 - "Community 73"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 75 - "Community 75"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.36
Nodes (6): _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test(), LdapFormData, _parse_ldap_form()

### Community 79 - "Community 79"
Cohesion: 0.28
Nodes (6): event_importance(), importance_rank(), types_at_least(), aggregate_incident_feed(), _fresh(), test_importance_table()

### Community 80 - "Community 80"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 81 - "Community 81"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 82 - "Community 82"
Cohesion: 0.29
Nodes (5): disk_role(), meta_facet_matches(), normalize_os_caption(), resolve_cpu_family(), _disk_role_label_ru()

### Community 83 - "Community 83"
Cohesion: 0.43
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 84 - "Community 84"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 85 - "Community 85"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 87 - "Community 87"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 88 - "Community 88"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 89 - "Community 89"
Cohesion: 0.40
Nodes (3): initDeviceLiveSearch(), clear(), render()

### Community 95 - "Community 95"
Cohesion: 0.60
Nodes (4): chartNote(), init(), apply(), applyChart()

### Community 103 - "Community 103"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **233 isolated node(s):** `ExitCode`, `Html`, `KeyRejected`, `Lines`, `StopAfterReply` (+228 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 694 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 2` to `Community 0`, `Community 3`, `Community 5`, `Community 8`, `Community 9`, `Community 11`, `Community 14`, `Community 16`, `Community 18`, `Community 23`, `Community 25`, `Community 27`, `Community 29`, `Community 32`, `Community 33`, `Community 34`, `Community 35`, `Community 41`, `Community 45`, `Community 49`, `Community 50`, `Community 51`, `Community 55`, `Community 56`, `Community 60`, `Community 62`, `Community 69`, `Community 78`, `Community 92`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Are the 177 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 177 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ExitCode`, `Html`, `KeyRejected` to the rest of the system?**
  _233 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05230678812812224 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 28` to `Community 1`, `Community 4`, `Community 17`, `Community 20`, `Community 54`, `Community 31`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Are the 109 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 109 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06054054054054054 - nodes in this community are weakly interconnected._