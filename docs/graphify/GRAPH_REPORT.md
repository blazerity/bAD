# Graph Report - bAD  (2026-11-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2225 nodes · 6393 edges · 120 communities (81 shown, 39 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 562 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `62fc5363`
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
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 110
- Community 111
- Community 112
- Community 113
- Community 117

## God Nodes (most connected - your core abstractions)
1. `Database` - 304 edges
2. `WebUser` - 96 edges
3. `post()` - 71 edges
4. `InventoryCollector` - 64 edges
5. `AgentConfig` - 63 edges
6. `utc_now()` - 52 edges
7. `_html()` - 52 edges
8. `Settings` - 45 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 40 edges

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

## Communities (120 total, 39 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (8): create_enrollment_grant(), try_local_login(), _compact_json(), Database, utc_now(), set_device_refresh_request(), list_integrations(), revoke()

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (81): require_web_user(), cookie_secure_for_request(), set_csrf_cookie(), merge_security_into_ops(), dump_session(), WebUser, default_digest_weekdays(), _backup_context() (+73 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (63): apply_user_presence_patch(), collect_hardware_serials(), _add(), enrich_hardware_meta(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type(), normalize_logged_on_list() (+55 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (46): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_delete_device_override() (+38 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (37): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+29 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (35): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatActions, Inventory, Uninstall, UpdateCheck (+27 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (32): device_panel_href(), format_logged_on_display(), request_device_uninstall(), start_new_uninstall_request_patch(), highlight_match(), resolve_device_ref(), _apply_bool_form_fields(), _apply_inventory_overlay() (+24 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (27): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _device_card_html(), digest_schedule_preview_ru(), digest_send_due() (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+14 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (25): _accumulate_hw_bars(), aggregate_incident_feed(), _fresh(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner(), build_dashboard_stats() (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (17): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (20): heartbeat(), health_snippet(), parse_iso(), parse_utc(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), refresh_request_pending() (+12 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (5): AgentApiException, IsAuthFailure, BadApiClient, EnrollResult, InventoryPostFailure

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (3): AgentUpdater, WindowsEventLog, Worker

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (5): InventoryCollector, MsftPhysicalDiskRow, Serial, UniqueId, WmiHelper

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (36): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+28 more)

### Community 18 - "Community 18"
Cohesion: 0.16
Nodes (4): AsciiReportWriter, HtmlReportWriter, ReportFormat, TimeFormat

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (21): apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url(), _iso_z(), key_path(), _load_size_check() (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.20
Nodes (7): CollectorError, Error, Section, VolumeInfo, FreeBytes, Letter, SizeBytes

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (20): require_web_admin(), device_silence_status(), effective_stale_after_seconds(), parse_site_stale_seconds(), filter_devices_by_wave(), _match(), normalize_wave_filter(), _attach_duplicate_signals() (+12 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 23 - "Community 23"
Cohesion: 0.10
Nodes (5): DeviceIdentity, PingCli, QuietFiles, TextLimit, BadAgent

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (3): BadCli, DoctorCli, UpdateCli

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (22): create_app(), dump_name_ok(), enrollment_code_hash(), new_device_signing_key(), _device_id(), _device_row(), _fingerprint(), _snap_count() (+14 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (26): CpuInfo, Cores, Logical, Name, HardwareInfo, BaseboardSerial, Battery, BiosManufacturer (+18 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (19): enroll(), rotate_device_key(), approve(), _clean_name(), create_request(), integration_from_token(), IntegrationError, is_integration_id() (+11 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (22): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, IInventoryCollector, InventorySnapshot, AgentVersion, CollectedAt (+14 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (16): _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval(), _smtp_password() (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (15): admin_token_valid(), ensure_bootstrap_secrets(), _persist(), get_data_key(), get_db(), get_session_secret(), _read_secret_file(), require_admin_token() (+7 more)

### Community 32 - "Community 32"
Cohesion: 0.15
Nodes (14): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody, EnrollRequest (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (3): UpdatePlan, UpdatePathUtil, VersionUtil

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (11): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), resolve_target_cached(), parse_semver() (+3 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (11): event_importance(), _bar_chart_labels(), _chassis_map_for_devices(), _device_inventory_signing_line(), _devices_catalog_filter_options(), events_page(), _facet_catalog_label_ok(), _normalize_overview_priority_feed() (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.19
Nodes (5): MinidumpBugcheck, Result, MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (10): ensure_bad_id_key(), mark_device_enrolled(), set_lock_timeout(), _assign_bad_ids(), _backfill_bad_ids(), _ensure_bad_id_column(), _rewrite_bad_ids(), run_bad_id_formula_migration() (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (11): ingest_uploaded_msi(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (5): delete_msi_version(), prune_old_msi_versions(), sync_from_github(), versions_pinned_in_config(), sort_key()

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (10): agent_minidump(), _copy_minidump(), cause_label(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header() (+2 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (9): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), load_session(), ldap_settings_test(), LdapFormData (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (3): AgentUninstaller, MsiexecLauncher, UninstallCli

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (3): AgentSigningKey, KeyPath, SkipFetchPath

### Community 49 - "Community 49"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (4): resolve_agent_updates_dir(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active()

### Community 52 - "Community 52"
Cohesion: 0.23
Nodes (8): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 55 - "Community 55"
Cohesion: 0.21
Nodes (5): Settings, https_first_status(), _secret_source(), secrets_status(), security_status()

### Community 56 - "Community 56"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (7): create_integration_request(), _display_serial(), _enforce_enroll_rate(), _integration_http_error(), poll_integration_request(), submit_enrollment_request(), client_ip()

### Community 58 - "Community 58"
Cohesion: 0.21
Nodes (3): adapt_sql(), CompatConnection, _split_sql_statements()

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.29
Nodes (6): connect_postgres(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes(), index_exists()

### Community 63 - "Community 63"
Cohesion: 0.27
Nodes (4): enroll_cleartext_blocked(), request_is_cleartext(), sensitive_over_http_blocked(), tls_mode_http()

### Community 64 - "Community 64"
Cohesion: 0.24
Nodes (7): _accept_policy(), _filter_policy_settings(), _policies_context(), policy_create(), policy_update(), PolicyFormData, _validate_update_target_pin()

### Community 65 - "Community 65"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 67 - "Community 67"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 70 - "Community 70"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 73 - "Community 73"
Cohesion: 0.36
Nodes (3): _cpu_for(), main(), seed_one()

### Community 74 - "Community 74"
Cohesion: 0.39
Nodes (3): decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 75 - "Community 75"
Cohesion: 0.32
Nodes (4): _accepted_inventory(), agent_report_html(), inventory(), InventoryRequest

### Community 78 - "Community 78"
Cohesion: 0.33
Nodes (3): importance_rank(), types_at_least(), types_exact_importance()

### Community 79 - "Community 79"
Cohesion: 0.43
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 80 - "Community 80"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 81 - "Community 81"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 82 - "Community 82"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 84 - "Community 84"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 85 - "Community 85"
Cohesion: 0.40
Nodes (3): initDeviceLiveSearch(), clear(), render()

### Community 90 - "Community 90"
Cohesion: 0.60
Nodes (4): chartNote(), init(), apply(), applyChart()

### Community 91 - "Community 91"
Cohesion: 0.50
Nodes (4): UpdateAction, Downgrade, None, Upgrade

### Community 98 - "Community 98"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **221 isolated node(s):** `AuthException`, `AuthFailed`, `Deferred`, `Error`, `Failures` (+216 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 673 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 6`, `Community 7`, `Community 12`, `Community 13`, `Community 21`, `Community 27`, `Community 29`, `Community 31`, `Community 35`, `Community 36`, `Community 39`, `Community 40`, `Community 41`, `Community 45`, `Community 46`, `Community 52`, `Community 55`, `Community 57`, `Community 60`, `Community 64`, `Community 75`, `Community 78`, `Community 95`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Are the 176 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 176 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AuthException`, `AuthFailed`, `Deferred` to the rest of the system?**
  _221 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0453168044077135 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 15` to `Community 24`, `Community 18`, `Community 14`, `Community 23`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `InventoryCollector` (e.g. with `BadCli.Collect()` and `PushCli.RunPush()`) actually correct?**
  _`InventoryCollector` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07259658580413297 - nodes in this community are weakly interconnected._