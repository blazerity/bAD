# Graph Report - bAD  (2026-11-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2209 nodes · 6383 edges · 111 communities (75 shown, 36 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 741 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `37ec14ae`
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
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 101
- Community 102
- Community 103
- Community 104
- Community 108

## God Nodes (most connected - your core abstractions)
1. `Database` - 303 edges
2. `Settings` - 122 edges
3. `WebUser` - 95 edges
4. `post()` - 70 edges
5. `InventoryCollector` - 64 edges
6. `AgentConfig` - 63 edges
7. `_html()` - 52 edges
8. `utc_now()` - 51 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 41 edges

## Surprising Connections (you probably didn't know these)
- `check_update()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_settings_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `effective_update_target_for_device()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `ingest_uploaded_msi()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `prune_old_msi_versions()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py

## Import Cycles
- None detected.

## Communities (111 total, 36 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (16): delete_msi_version(), ops_update_signals(), set_latest_msi_version(), versions_pinned_in_config(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), heartbeat() (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (77): get_session_secret(), Settings, cookie_secure_for_request(), set_csrf_cookie(), sensitive_over_http_blocked(), WebUser, _backup_context(), backups_key_escrow_download() (+69 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (37): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+29 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (42): admin_server_update_set_branch(), admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (31): health_snippet(), parse_iso(), event_importance(), importance_rank(), types_at_least(), types_exact_importance(), normalize_os_caption(), aggregate_incident_feed() (+23 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (39): _accepted_inventory(), admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_status(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy(), admin_device_config() (+31 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (33): create_integration_request(), _integration_http_error(), poll_integration_request(), rotate_device_key(), admin_token_valid(), get_data_key(), get_db(), require_admin_token() (+25 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (21): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (26): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+18 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (18): _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval(), _smtp_password() (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (27): request_device_refresh_api(), device_panel_href(), set_device_refresh_request(), highlight_match(), event_visual(), resolve_device_ref(), _apply_inventory_overlay(), _archive_device() (+19 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (5): BadCli, DoctorCli, IInventoryCollector, ServerUrlRules, UpdateCli

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (21): require_web_admin(), device_silence_status(), effective_stale_after_seconds(), parse_site_stale_seconds(), enrich_overview_ops_signals(), filter_devices_by_wave(), _match(), normalize_wave_filter() (+13 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (5): AsciiReportWriter, HtmlReportWriter, ReportFormat, ReportPathResolver, TimeFormat

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (17): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (22): build_hardware_email(), build_inventory_digest_email(), _chassis_key(), default_digest_weekdays(), _device_card_html(), digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours() (+14 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (5): AgentApiException, IsAuthFailure, BadApiClient, EnrollResult, InventoryPostFailure

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (35): CpuInfo, Cores, Logical, Name, GpuInfo, AdapterRamBytes, DriverVersion, Name (+27 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (15): AntivirusProductInfo, Name, ProductState, CollectorError, Error, Section, SecurityInfo, Antivirus (+7 more)

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (5): DeviceIdentity, PingCli, QuietFiles, TextLimit, BadAgent

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (18): parse_utc(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), refresh_request_pending(), _utc_iso_ge(), cancel_device_uninstall(), clear_uninstall_request_patch() (+10 more)

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (24): create_app(), encrypt_secret(), cause_label(), dump_name_ok(), enrollment_code_hash(), new_device_signing_key(), _device_id(), _device_row() (+16 more)

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (22): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _format_free_gib() (+14 more)

### Community 27 - "Community 27"
Cohesion: 0.07
Nodes (28): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, HardwareInfo, BaseboardSerial (+20 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (21): HeartbeatActions, Inventory, Uninstall, UpdateCheck, UploadMinidump, HeartbeatServerResponse, Actions, Config (+13 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (15): create_enrollment_grant(), AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody (+7 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (4): AgentUninstaller, MsiexecLauncher, UninstallCli, WindowsEventLog

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (11): MsftPhysicalDiskRow, Serial, UniqueId, DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.16
Nodes (14): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_role(), format_cpu_short(), _intel_core_i_family(), _intel_family() (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (4): ConfigStore, ConfigPath, LogsDir, ProgramDataDir

### Community 36 - "Community 36"
Cohesion: 0.19
Nodes (5): MinidumpBugcheck, Result, MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (11): HeavySectionCache, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InstalledProgram, Name, Publisher (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (10): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), dump_session(), load_session(), ldap_settings_test() (+2 more)

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (12): apply_user_presence_patch(), collect_hardware_serials(), _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line() (+4 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (10): connect_postgres(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes(), index_exists(), set_lock_timeout(), _ensure_bad_id_column() (+2 more)

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (4): AgentSigningKey, KeyPath, SkipFetchPath, InventorySignTrace

### Community 44 - "Community 44"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (12): enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), disk_bucket_from_fixed_bytes(), format_ram_ddr(), format_ram_gib(), format_ram_list_cell(), ram_bucket() (+4 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (7): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), _assign_bad_ids(), _backfill_bad_ids(), _rewrite_bad_ids(), run_bad_id_formula_migration()

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (9): agent_minidump(), _copy_minidump(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header(), read_kernel_header() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.19
Nodes (7): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 52 - "Community 52"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 53 - "Community 53"
Cohesion: 0.17
Nodes (8): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), _fernet_from_key(), generate_data_key(), generate_session_secret()

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (7): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf(), build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 56 - "Community 56"
Cohesion: 0.16
Nodes (10): _accept_policy(), _apply_bool_form_fields(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policy_create(), policy_update(), PolicyFormData (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.26
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 60 - "Community 60"
Cohesion: 0.23
Nodes (5): https_first_status(), merge_security_into_ops(), _secret_source(), secrets_status(), security_status()

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (3): SigningKeyFetchResult, EnrollmentProof, ProofPath

### Community 63 - "Community 63"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.22
Nodes (6): format_logged_on_display(), normalize_logged_on_user(), _device_inventory_nav(), _disk_overview_line(), _format_bytes(), _format_os()

### Community 67 - "Community 67"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 68 - "Community 68"
Cohesion: 0.28
Nodes (5): _display_serial(), _enforce_enroll_rate(), enroll(), submit_enrollment_request(), mark_device_enrolled()

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 72 - "Community 72"
Cohesion: 0.38
Nodes (3): panel_tls_mode(), patch_security_for_qa(), qa_ui_active()

### Community 73 - "Community 73"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 74 - "Community 74"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 77 - "Community 77"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 78 - "Community 78"
Cohesion: 0.33
Nodes (3): archive_device(), restore_device(), revoke_device()

### Community 79 - "Community 79"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 80 - "Community 80"
Cohesion: 0.40
Nodes (3): initDeviceLiveSearch(), clear(), render()

### Community 82 - "Community 82"
Cohesion: 0.60
Nodes (4): chartNote(), init(), apply(), applyChart()

### Community 83 - "Community 83"
Cohesion: 0.50
Nodes (4): UpdateAction, Downgrade, None, Upgrade

### Community 90 - "Community 90"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **222 isolated node(s):** `bad-server`, `AuthException`, `AuthFailed`, `Deferred`, `Error` (+217 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 666 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 10`, `Community 11`, `Community 14`, `Community 16`, `Community 17`, `Community 22`, `Community 29`, `Community 39`, `Community 41`, `Community 45`, `Community 47`, `Community 48`, `Community 49`, `Community 53`, `Community 56`, `Community 60`, `Community 68`, `Community 69`, `Community 78`, `Community 91`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 175 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 175 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `AuthException`, `AuthFailed` to the rest of the system?**
  _222 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.04101161995898838 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 7` to `Community 13`, `Community 18`, `Community 21`, `Community 15`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 106 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 106 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07998350855493713 - nodes in this community are weakly interconnected._