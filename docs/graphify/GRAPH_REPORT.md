# Graph Report - bAD-simplify-d100  (2026-11-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2112 nodes · 6065 edges · 105 communities (71 shown, 34 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 701 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `868077b5`
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
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 98
- Community 99
- Community 103

## God Nodes (most connected - your core abstractions)
1. `Database` - 296 edges
2. `Settings` - 123 edges
3. `WebUser` - 95 edges
4. `post()` - 70 edges
5. `InventoryCollector` - 64 edges
6. `_html()` - 54 edges
7. `AgentConfig` - 51 edges
8. `utc_now()` - 48 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 35 edges

## Surprising Connections (you probably didn't know these)
- `delete_msi_version()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `ingest_uploaded_msi()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `prune_old_msi_versions()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `sync_from_github()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `admin_agent_update_delete()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py

## Import Cycles
- None detected.

## Communities (105 total, 34 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (81): admin_server_update_set_branch(), Settings, set_csrf_cookie(), sensitive_over_http_blocked(), releases_dir(), dump_session(), WebUser, https_panel_url() (+73 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (18): admin_delete_device_override(), admin_delete_policy(), admin_device_config(), archive_device(), delete_device(), issue_agent_signing_key(), list_events(), restore_device() (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (20): AsciiReportWriter, HtmlReportWriter, ReportFormat, TimeFormat, backup_filename(), backup_keys_status(), backup_status(), _chmod_private() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (22): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), is_bad_id(), adapt_sql(), CompatConnection, CompatCursor, connect_postgres() (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (39): admin_server_update_set_token(), utc_now(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+31 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (28): device_silence_status(), health_snippet(), parse_utc(), importance_rank(), types_at_least(), _accumulate_hw_bars(), aggregate_incident_feed(), build_config_winner() (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (28): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), default_digest_weekdays(), _device_card_html(), digest_schedule_preview_ru() (+20 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (23): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), _read_server_version(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+15 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (25): admin_enrollment_rotate(), admin_set_device_override(), admin_update_policy(), _enforce_enroll_rate(), _enrollment_request_id(), health(), put_device_tags(), rotate_device_key() (+17 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (19): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+11 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (3): AgentUpdater, WindowsEventLog, Worker

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (16): list_devices(), require_web_admin(), effective_stale_after_seconds(), parse_site_stale_seconds(), normalize_wave_filter(), _attach_duplicate_signals(), devices_csv_export(), _devices_filter_chips() (+8 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (26): _device_card(), request_device_refresh_api(), device_panel_href(), set_device_refresh_request(), cancel_device_uninstall(), request_device_uninstall(), highlight_match(), resolve_device_ref() (+18 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (24): enrich_hardware_meta(), _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_bucket_from_fixed_bytes(), disk_role(), format_cpu_short() (+16 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (6): AgentApiException, IsAuthFailure, AgentSigningKey, KeyPath, SkipFetchPath, BadApiClient

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (21): admin_agent_config_defaults(), admin_agent_update_sync(), admin_create_policy(), admin_get_policy(), admin_list_policies(), admin_security_status(), admin_server_update_apply(), admin_server_update_apply_status() (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.06
Nodes (30): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+22 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (19): enroll(), admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token() (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.12
Nodes (19): apply_user_presence_patch(), collect_hardware_serials(), _add(), format_logged_on_display(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type(), normalize_logged_on_list() (+11 more)

### Community 23 - "Community 23"
Cohesion: 0.13
Nodes (19): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), _parse_utc_iso(), refresh_request_pending(), _utc_iso_ge(), clear_uninstall_request_patch() (+11 more)

### Community 24 - "Community 24"
Cohesion: 0.16
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (28): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor, HardwareInfo, BaseboardSerial (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.12
Nodes (4): BadCli, IInventoryCollector, ReportPathResolver, UpdateCli

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (10): delete_msi_version(), prune_old_msi_versions(), set_latest_msi_version(), versions_pinned_in_config(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_upload() (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (11): enrollment_rotation_signals(), enrollment_status(), mark_enrollment_wave_done(), build_bootstrap_checklist(), build_bootstrap_progress(), https_first_status(), merge_security_into_ops(), _secret_source() (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 30 - "Community 30"
Cohesion: 0.10
Nodes (13): event_importance(), build_attention_queue(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active(), _bar_chart_labels(), _device_inventory_signing_line(), _devices_catalog_filter_options() (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (16): UpdateAction, Downgrade, None, Upgrade, UpdateCheckResponse, Action, Desired, MsiName (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.09
Nodes (21): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+13 more)

### Community 33 - "Community 33"
Cohesion: 0.24
Nodes (20): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _format_free_gib() (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (13): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals(), resolve_target_cached() (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.11
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (15): create_enrollment_grant(), create_app(), enrollment_code_hash(), generate_token(), new_device_signing_key(), _device_id(), _snap_count(), test_enrollment_request_waits_for_admin() (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.17
Nodes (3): HardwareMaps, MinidumpBugcheck, Result

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (10): agent_update_msi(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json() (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (12): create_integration_request(), _integration_http_error(), poll_integration_request(), approve(), _clean_name(), create_request(), IntegrationError, is_integration_id() (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (9): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), load_session(), ldap_settings_test(), LdapFormData (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (9): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), encrypt_secret(), _fernet_from_key(), generate_data_key() (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 54 - "Community 54"
Cohesion: 0.14
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 55 - "Community 55"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 58 - "Community 58"
Cohesion: 0.27
Nodes (7): enrollment_token_file(), mark_device_enrolled(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file(), hash_secret()

### Community 59 - "Community 59"
Cohesion: 0.24
Nodes (3): MsftPhysicalDiskRow, Serial, UniqueId

### Community 60 - "Community 60"
Cohesion: 0.31
Nodes (5): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 61 - "Community 61"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 63 - "Community 63"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.56
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.36
Nodes (3): _cpu_for(), main(), seed_one()

### Community 67 - "Community 67"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 68 - "Community 68"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 69 - "Community 69"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (3): inventory(), inventory_budget_error(), sanitize_inventory_payload()

### Community 71 - "Community 71"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 72 - "Community 72"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 73 - "Community 73"
Cohesion: 0.43
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 74 - "Community 74"
Cohesion: 0.33
Nodes (4): _device_inventory_nav(), _disk_overview_line(), _format_bytes(), _format_os()

### Community 75 - "Community 75"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 79 - "Community 79"
Cohesion: 0.60
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 81 - "Community 81"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **221 isolated node(s):** `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+216 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 648 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 11`, `Community 12`, `Community 15`, `Community 16`, `Community 19`, `Community 21`, `Community 22`, `Community 23`, `Community 27`, `Community 28`, `Community 30`, `Community 36`, `Community 39`, `Community 44`, `Community 45`, `Community 47`, `Community 48`, `Community 58`, `Community 70`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Are the 173 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 173 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentLocalKeys`, `ApiKey`, `CollectHardware` to the rest of the system?**
  _221 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07545787545787545 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 13` to `Community 65`, `Community 42`, `Community 2`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 107 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 107 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.046534653465346534 - nodes in this community are weakly interconnected._