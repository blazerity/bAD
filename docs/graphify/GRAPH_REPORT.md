# Graph Report - bAD  (2026-11-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2215 nodes · 6414 edges · 110 communities (74 shown, 36 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 756 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1c1e7e53`
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
- Community 84
- Community 85
- Community 86
- Community 87
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 100
- Community 101
- Community 102
- Community 103
- Community 107

## God Nodes (most connected - your core abstractions)
1. `Database` - 309 edges
2. `Settings` - 127 edges
3. `WebUser` - 98 edges
4. `post()` - 73 edges
5. `InventoryCollector` - 64 edges
6. `AgentConfig` - 63 edges
7. `_html()` - 54 edges
8. `utc_now()` - 52 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 39 edges

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

## Communities (110 total, 36 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (15): set_latest_msi_version(), issue_agent_signing_key(), try_local_login(), _compact_json(), Database, set_device_refresh_request(), cancel_device_uninstall(), request_device_uninstall() (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (87): Settings, set_csrf_cookie(), sensitive_over_http_blocked(), dump_session(), WebUser, https_panel_url(), read_domain_from_env(), resolve_device_ref() (+79 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (40): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+32 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (43): heartbeat(), device_silence_status(), parse_iso(), parse_utc(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), refresh_request_pending() (+35 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (27): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), _split_sql_statements() (+19 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (45): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_delete_device_override() (+37 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (31): _stale_pass(), _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), default_digest_weekdays(), _device_card_html() (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (38): utc_now(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token() (+30 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (5): AgentApiException, IsAuthFailure, BadApiClient, InventoryPostFailure, Worker

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (26): require_web_admin(), effective_stale_after_seconds(), parse_site_stale_seconds(), event_importance(), build_bootstrap_checklist(), build_bootstrap_progress(), enrich_overview_ops_signals(), normalize_wave_filter() (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (23): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (31): HeartbeatActions, Inventory, Uninstall, UpdateCheck, UploadMinidump, HeartbeatServerResponse, Actions, Config (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (5): AsciiReportWriter, HtmlReportWriter, ReportFormat, ReportPathResolver, TimeFormat

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (5): BadCli, IInventoryCollector, PushCli, ServerUrlRules, UpdateCli

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (21): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z() (+13 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (5): AgentUpdater, UpdatePlan, MsiexecLauncher, UpdatePathUtil, VersionUtil

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (32): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, HardwareInfo, BaseboardSerial (+24 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (15): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (23): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key() (+15 more)

### Community 24 - "Community 24"
Cohesion: 0.17
Nodes (22): create_app(), dump_name_ok(), generate_token(), new_device_signing_key(), _device_id(), _device_row(), _fingerprint(), _snap_count() (+14 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (26): AntivirusProductInfo, Name, ProductState, CpuInfo, Cores, Logical, Name, DiskInfo (+18 more)

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (11): HeavySectionCache, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InstalledProgram, Name, Publisher (+3 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (15): create_enrollment_grant(), AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (13): AgentSigningKey, KeyPath, SkipFetchPath, UpdateCheckResponse, Action, Desired, MsiName, Reason (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.15
Nodes (16): poll_integration_request(), approve(), _clean_name(), create_request(), integration_from_token(), IntegrationError, is_integration_id(), _new_id() (+8 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (15): collect_hardware_serials(), _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line(), event_match_label() (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (25): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+17 more)

### Community 32 - "Community 32"
Cohesion: 0.16
Nodes (16): enroll(), admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token() (+8 more)

### Community 33 - "Community 33"
Cohesion: 0.15
Nodes (15): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_role(), format_cpu_short(), _intel_core_i_family(), _intel_family() (+7 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (15): device_panel_href(), health_snippet(), _apply_inventory_overlay(), _archive_device(), _chassis_map_for_devices(), _chassis_type_from_device(), _device_config_context(), device_delete() (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.13
Nodes (4): DeviceIdentity, PingCli, TextLimit, BadAgent

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 39 - "Community 39"
Cohesion: 0.14
Nodes (9): enrollment_rotation_signals(), enrollment_status(), mark_enrollment_wave_done(), https_first_status(), merge_security_into_ops(), _secret_source(), secrets_status(), security_status() (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.18
Nodes (3): AgentUninstaller, UninstallCli, WindowsEventLog

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (11): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), load_session(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save() (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (7): admin_enrollment_rotate(), create_integration_request(), _display_serial(), _enforce_enroll_rate(), _integration_http_error(), submit_enrollment_request(), client_ip()

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (7): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (9): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), encrypt_secret(), _fernet_from_key(), generate_data_key() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 50 - "Community 50"
Cohesion: 0.15
Nodes (6): _accepted_inventory(), agent_report_html(), inventory(), InventoryRequest, _panel_css(), render_device_report()

### Community 51 - "Community 51"
Cohesion: 0.24
Nodes (10): enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), disk_bucket_from_fixed_bytes(), format_ram_ddr(), format_ram_gib(), format_ram_list_cell(), ram_bucket() (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 54 - "Community 54"
Cohesion: 0.27
Nodes (5): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 56 - "Community 56"
Cohesion: 0.24
Nodes (4): delete_msi_version(), prune_old_msi_versions(), versions_pinned_in_config(), _enrollment_msi_name()

### Community 57 - "Community 57"
Cohesion: 0.27
Nodes (7): enrollment_token_file(), mark_device_enrolled(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), hash_secret()

### Community 58 - "Community 58"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 60 - "Community 60"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.42
Nodes (6): cause_label(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header()

### Community 64 - "Community 64"
Cohesion: 0.31
Nodes (6): _accept_policy(), _filter_policy_settings(), _policies_context(), policy_create(), policy_update(), PolicyFormData

### Community 65 - "Community 65"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 66 - "Community 66"
Cohesion: 0.36
Nodes (3): MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 68 - "Community 68"
Cohesion: 0.29
Nodes (5): format_logged_on_display(), _device_inventory_nav(), _disk_overview_line(), _format_bytes(), _format_os()

### Community 70 - "Community 70"
Cohesion: 0.38
Nodes (3): agent_minidump(), _copy_minidump(), unlink_dump()

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 72 - "Community 72"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 73 - "Community 73"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 74 - "Community 74"
Cohesion: 0.53
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 75 - "Community 75"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 76 - "Community 76"
Cohesion: 0.40
Nodes (3): initDeviceLiveSearch(), clear(), render()

### Community 80 - "Community 80"
Cohesion: 0.60
Nodes (4): init(), apply(), applyChart(), applyProblems()

### Community 81 - "Community 81"
Cohesion: 0.50
Nodes (4): UpdateAction, Downgrade, None, Upgrade

### Community 87 - "Community 87"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **222 isolated node(s):** `Error`, `Section`, `bad-server`, `AgentLocalKeys`, `ApiKey` (+217 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 673 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 8` to `Community 16`, `Community 19`, `Community 35`, `Community 15`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 181 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 181 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Error`, `Section`, `bad-server` to the rest of the system?**
  _222 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.040353786622443336 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 9`, `Community 18`, `Community 22`, `Community 27`, `Community 29`, `Community 30`, `Community 32`, `Community 34`, `Community 39`, `Community 41`, `Community 44`, `Community 48`, `Community 50`, `Community 56`, `Community 57`, `Community 64`, `Community 70`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 111 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0680018630647415 - nodes in this community are weakly interconnected._