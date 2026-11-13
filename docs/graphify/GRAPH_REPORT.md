# Graph Report - bAD  (2026-11-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2418 nodes · 7063 edges · 121 communities (82 shown, 39 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 779 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `91abc16b`
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
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
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
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 104
- Community 105
- Community 106
- Community 107
- Community 113
- Community 114
- Community 115
- Community 118

## God Nodes (most connected - your core abstractions)
1. `Database` - 306 edges
2. `Settings` - 125 edges
3. `WebUser` - 101 edges
4. `post()` - 71 edges
5. `AgentConfig` - 69 edges
6. `InventoryCollector` - 65 edges
7. `_html()` - 55 edges
8. `utc_now()` - 52 edges
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

## Communities (121 total, 39 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (17): versions_pinned_in_config(), admin_delete_device_override(), seed_default_admin(), _compact_json(), Database, utc_now(), set_device_refresh_request(), cancel_device_uninstall() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (76): cookie_secure_for_request(), set_csrf_cookie(), dump_session(), WebUser, default_digest_weekdays(), _apply_bool_form_fields(), _backup_context(), backups_key_escrow_download() (+68 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (9): BadCli, CliColumns, IInventoryCollector, PushCli, ServiceChannel, ServiceCli, UninstallCli, UpdateCli (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (44): apply_user_presence_patch(), collect_hardware_serials(), _add(), enrich_hardware_meta(), format_logged_on_display(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type() (+36 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (43): AgentConfig, AgentLocalKeys, ApiKey, BadId, CollectHardware, CollectSoftware, CollectUsers, EnrollmentCode (+35 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (53): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bag_delta(), _bios_token(), _both_lists(), _bugcheck_code() (+45 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (8): AgentApiException, IsAuthFailure, IsBoardChanged, BadApiClient, EnrollResult, InventoryPostFailure, InvalidKeyReset, Worker

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (14): CliLine, CliOutcome, ExitCode, Html, KeyRejected, Lines, StopAfterReply, Tail (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (36): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+28 more)

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (30): require_web_admin(), device_silence_status(), effective_recent_after_seconds(), effective_stale_after_seconds(), stale_days_form(), filter_devices_by_wave(), _match(), normalize_wave_filter() (+22 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (36): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_create_policy(), admin_delete_policy(), admin_device_config(), admin_get_policy() (+28 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (23): OfflineFlushResult, AuthException, AuthFailed, BoardChanged, Deferred, Error, Failures, NextRetryUtc (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (26): build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _compact_event_html(), _device_card_html(), digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours() (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (22): heartbeat(), badge_recent_after_seconds(), health_snippet(), parse_iso(), parse_site_recent_seconds(), parse_site_stale_seconds(), parse_utc(), clear_refresh_meta_patch() (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (5): AsciiReportWriter, HtmlReportWriter, ReportFormat, ReportPathResolver, TimeFormat

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (12): sensitive_over_http_blocked(), tls_mode_http(), _read_server_version(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active(), https_first_status(), merge_security_into_ops() (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (23): enroll(), rotate_device_key(), bad_id_from_board(), ensure_bad_id_key(), is_bad_id(), normalize_machine_guid(), random_bad_id(), encrypt_secret() (+15 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (17): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (21): apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url(), _iso_z(), key_path(), _load_size_check() (+13 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (19): admin_token_valid(), ensure_bootstrap_secrets(), _persist(), get_data_key(), get_db(), get_session_secret(), load_ldap_view(), _read_secret_file() (+11 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (22): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, BadId, CollectedAt (+14 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (21): admin_agent_update_sync(), admin_agent_update_upload(), admin_enrollment_rotate(), admin_server_update_apply(), admin_server_update_msi_poll(), admin_server_update_msi_trigger(), _admin_server_update_request(), admin_server_update_rollback() (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (10): adapt_sql(), CompatConnection, connect_postgres(), _split_sql_statements(), _utc_iso(), connect_autocommit(), create_index_concurrently(), ensure_trgm_search_indexes() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (4): AgentUpdater, UpdatePlan, UpdatePathUtil, VersionUtil

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (28): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor, HardwareInfo, BaseboardSerial (+20 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (15): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), resolve_target_cached(), parse_semver(), resolve_target_msi() (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (15): normalize_os_caption(), build_attention_queue(), build_config_winner(), build_dashboard_stats(), _hbar_block(), build_wave_counts(), chart_filter_href(), device_has_agent_local() (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.11
Nodes (10): _accepted_inventory(), create_enrollment_grant(), issue_agent_signing_key(), _log_inventory_signature(), decrypt_secret(), _fernet_from_key(), enrollment_code_hash(), inventory_signing_bytes() (+2 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (15): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody, EnrollRequest (+7 more)

### Community 34 - "Community 34"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (20): create_app(), dump_name_ok(), _bad_id(), _device_row(), _fingerprint(), _snap_count(), test_agent_report_html_is_enrolled_card_without_admin(), test_enrollment_request_waits_for_admin() (+12 more)

### Community 36 - "Community 36"
Cohesion: 0.09
Nodes (22): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+14 more)

### Community 37 - "Community 37"
Cohesion: 0.19
Nodes (5): MinidumpBugcheck, Result, MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.13
Nodes (5): delete_msi_version(), is_newer(), ops_update_signals(), prune_old_msi_versions(), set_latest_msi_version()

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (4): DeviceIdentity, QuietFiles, TextLimit, BadAgent

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (9): _download_bytes(), fetch_latest_release_assets(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), _cpu_for(), main() (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (12): event_importance(), aggregate_incident_feed(), _fresh(), _attach_duplicate_signals(), _bar_chart_labels(), _devices_catalog_filter_options(), _facet_catalog_label_ok(), _flash_check() (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.19
Nodes (4): AgentSigningKey, KeyPath, SkipFetchPath, InventorySignTrace

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (9): _notify_check_groups(), _Db, _media_block(), _Settings, test_mail_checkbox_labels_and_groups(), test_notify_grid_collapses_at_phone_width(), test_recent_threshold_and_badge(), test_stale_days_post_and_get() (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 46 - "Community 46"
Cohesion: 0.20
Nodes (10): agent_minidump(), _copy_minidump(), cause_label(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header() (+2 more)

### Community 47 - "Community 47"
Cohesion: 0.12
Nodes (14): UpdateAction, Downgrade, None, Upgrade, UpdateCheckResponse, Action, Desired, MsiName (+6 more)

### Community 48 - "Community 48"
Cohesion: 0.19
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (11): get_settings(), _panel_css(), render_device_report(), _bad_id(), _enroll(), _html(), _panel(), test_card_without_snapshot_keeps_empty_sections() (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.15
Nodes (9): authenticate_web_user(), current_web_user(), try_local_login(), dump_flash(), load_flash(), load_session(), _load_signed_payload(), password_submit() (+1 more)

### Community 51 - "Community 51"
Cohesion: 0.19
Nodes (8): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_device_enrolled(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 52 - "Community 52"
Cohesion: 0.35
Nodes (13): _csrf(), _fp(), _hashes(), _login(), _request(), test_allow_any_bad_id_issues_key(), test_allow_empty_device_creates_card_and_flash_is_once(), test_allow_live_card_rotates_key() (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.12
Nodes (15): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 55 - "Community 55"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.44
Nodes (13): _allow(), _claim(), _device_count(), _fp(), _login(), _request(), _snaps(), test_bad_id_required() (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.19
Nodes (7): create_integration_request(), _display_serial(), _enforce_enroll_rate(), submit_enrollment_request(), client_ip(), enroll_cleartext_blocked(), request_is_cleartext()

### Community 60 - "Community 60"
Cohesion: 0.15
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, BadId, ConfigLocal (+5 more)

### Community 62 - "Community 62"
Cohesion: 0.21
Nodes (7): _accept_policy(), _filter_policy_settings(), _policies_context(), policy_create(), policy_update(), PolicyFormData, _validate_update_target_pin()

### Community 65 - "Community 65"
Cohesion: 0.24
Nodes (3): MsftPhysicalDiskRow, Serial, UniqueId

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 69 - "Community 69"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 70 - "Community 70"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.20
Nodes (9): reject(), revoke(), _set_status(), _clear_session_cookie(), _integration_action(), integrations_approve(), integrations_reject(), integrations_revoke() (+1 more)

### Community 73 - "Community 73"
Cohesion: 0.22
Nodes (4): _chassis_map_for_devices(), events_page(), overview_search_json(), _overview_search_users()

### Community 74 - "Community 74"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 77 - "Community 77"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 78 - "Community 78"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 79 - "Community 79"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (3): importance_rank(), types_at_least(), types_exact_importance()

### Community 83 - "Community 83"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 84 - "Community 84"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 86 - "Community 86"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 88 - "Community 88"
Cohesion: 0.33
Nodes (3): _archive_device(), device_archive(), device_restore()

### Community 89 - "Community 89"
Cohesion: 0.40
Nodes (3): build_bootstrap_checklist(), build_bootstrap_progress(), tls_panel_mode()

### Community 90 - "Community 90"
Cohesion: 0.53
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 91 - "Community 91"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 97 - "Community 97"
Cohesion: 0.60
Nodes (4): chartNote(), init(), apply(), applyChart()

### Community 102 - "Community 102"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **233 isolated node(s):** `bad-server`, `AuthException`, `AuthFailed`, `BoardChanged`, `Deferred` (+228 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 695 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 1`, `Community 5`, `Community 10`, `Community 11`, `Community 14`, `Community 15`, `Community 17`, `Community 18`, `Community 19`, `Community 21`, `Community 22`, `Community 24`, `Community 25`, `Community 28`, `Community 32`, `Community 39`, `Community 42`, `Community 46`, `Community 49`, `Community 50`, `Community 51`, `Community 59`, `Community 62`, `Community 71`, `Community 73`, `Community 82`, `Community 87`, `Community 88`, `Community 95`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Are the 177 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 177 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `AuthException`, `AuthFailed` to the rest of the system?**
  _233 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.046143250688705235 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 6` to `Community 2`, `Community 4`, `Community 7`, `Community 40`, `Community 16`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Are the 109 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 109 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06523005241700641 - nodes in this community are weakly interconnected._