# Graph Report - workspace  (2026-11-03)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1994 nodes · 5718 edges · 99 communities (73 shown, 26 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 468 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ade19af9`
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
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 97

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

## Communities (99 total, 26 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (35): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file() (+27 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (46): admin_server_update_apply(), admin_server_update_apply_status(), admin_server_update_msi_trigger(), _admin_server_update_request(), admin_server_update_rollback(), admin_server_update_set_branch(), admin_server_update_set_token(), admin_server_update_status() (+38 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (4): list_devices(), list_events(), try_local_login(), Database

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (37): backup_keys_status(), cookie_secure_for_request(), set_csrf_cookie(), format_logged_on_display(), sensitive_over_http_blocked(), default_digest_weekdays(), dump_notify_flags(), parse_recipients() (+29 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (30): device_silence_status(), health_snippet(), parse_utc(), importance_rank(), types_at_least(), _accumulate_hw_bars(), aggregate_incident_feed(), build_attention_queue() (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (29): _stale_pass(), _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _device_card_html(), digest_schedule_preview_ru() (+21 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+15 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (9): InventoryCollector, CollectorError, Error, Section, SecurityInfo, Antivirus, SecureBoot, TpmPresent (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (32): https_panel_url(), read_domain_from_env(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), _device_merge_page() (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (11): bad_id_for_device(), ensure_bad_id_key(), set_lock_timeout(), _assign_bad_ids(), _backfill_bad_ids(), _backfill_device_meta(), _ensure_bad_id_column(), _rewrite_bad_ids() (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (9): AgentUpdater, UpdateAction, Downgrade, None, Upgrade, UpdatePlan, MsiexecLauncher, UpdatePathUtil (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (24): effective_stale_after_seconds(), parse_site_stale_seconds(), event_importance(), enrich_overview_ops_signals(), normalize_wave_filter(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active() (+16 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (24): set_latest_msi_version(), admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_upload(), admin_device_config(), admin_enrollment_rotate(), admin_get_policy(), admin_list_policies() (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (16): backup_filename(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup(), run_pg_dump() (+8 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (32): require_web_admin(), device_panel_href(), WebUser, resolve_device_ref(), device_archive(), _device_config_context(), device_config_override_save(), device_delete() (+24 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (34): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, GpuInfo, AdapterRamBytes (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (22): create_integration_request(), enroll(), _integration_http_error(), poll_integration_request(), rotate_device_key(), seed_default_admin(), approve(), _clean_name() (+14 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (27): AntivirusProductInfo, Name, ProductState, CpuInfo, Cores, Logical, Name, DiskInfo (+19 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (10): adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), _split_sql_statements(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index() (+2 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (3): AssemblyProbe, DeviceIdentity, BadAgent

### Community 23 - "Community 23"
Cohesion: 0.20
Nodes (22): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key() (+14 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (11): heartbeat(), inventory(), request_device_refresh_api(), utc_now(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending() (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (17): apply_user_presence_patch(), collect_hardware_serials(), _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line() (+9 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (13): _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+5 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (4): HardwareMaps, MsftPhysicalDiskRow, Serial, UniqueId

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (14): admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token(), require_web_user() (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.10
Nodes (8): delete_msi_version(), is_newer(), ops_update_signals(), admin_agent_update_delete(), admin_agent_update_status(), admin_agent_update_sync(), agent_update_msi(), _enrollment_msi_name()

### Community 32 - "Community 32"
Cohesion: 0.16
Nodes (13): ingest_uploaded_msi(), prune_old_msi_versions(), sync_from_github(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset() (+5 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.15
Nodes (15): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_role(), format_cpu_short(), _intel_core_i_family(), _intel_family() (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 36 - "Community 36"
Cohesion: 0.16
Nodes (12): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+4 more)

### Community 37 - "Community 37"
Cohesion: 0.15
Nodes (12): sanitize_conditions(), AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (3): AgentUninstaller, UninstallCli, WindowsEventLog

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (13): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), _parse_utc_iso(), request_device_uninstall() (+5 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (5): versions_pinned_in_config(), admin_create_policy(), admin_set_device_override(), admin_update_policy(), put_device_tags()

### Community 45 - "Community 45"
Cohesion: 0.17
Nodes (11): authenticate_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.21
Nodes (11): enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), disk_bucket_from_fixed_bytes(), format_ram_ddr(), format_ram_gib(), format_ram_list_cell(), ram_bucket() (+3 more)

### Community 47 - "Community 47"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.26
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 57 - "Community 57"
Cohesion: 0.18
Nodes (10): _apply_bool_form_fields(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policies_page(), policy_create(), policy_edit_page(), policy_update() (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.24
Nodes (4): _encode_crockford(), decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 61 - "Community 61"
Cohesion: 0.24
Nodes (6): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), resolve_target_cached(), resolve_target_msi()

### Community 65 - "Community 65"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 66 - "Community 66"
Cohesion: 0.33
Nodes (4): ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 67 - "Community 67"
Cohesion: 0.31
Nodes (3): _cpu_for(), main(), seed_one()

### Community 69 - "Community 69"
Cohesion: 0.28
Nodes (6): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key(), generate_session_secret()

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (3): admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 73 - "Community 73"
Cohesion: 0.29
Nodes (3): current_web_user(), dump_session(), load_session()

### Community 74 - "Community 74"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 75 - "Community 75"
Cohesion: 0.43
Nodes (4): build_server_runtime(), _probe_database(), _process_memory_bytes(), reset_process_start()

### Community 76 - "Community 76"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 77 - "Community 77"
Cohesion: 0.33
Nodes (3): parse_semver(), _semver_equal(), sort_key()

### Community 78 - "Community 78"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 79 - "Community 79"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 80 - "Community 80"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 82 - "Community 82"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **216 isolated node(s):** `AuthException`, `AuthFailed`, `Deferred`, `Error`, `Failures` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 617 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 2` to `Community 0`, `Community 3`, `Community 4`, `Community 5`, `Community 9`, `Community 11`, `Community 13`, `Community 14`, `Community 16`, `Community 17`, `Community 19`, `Community 21`, `Community 24`, `Community 25`, `Community 28`, `Community 30`, `Community 31`, `Community 32`, `Community 40`, `Community 44`, `Community 45`, `Community 57`, `Community 61`, `Community 69`, `Community 72`, `Community 73`, `Community 77`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 99 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AuthException`, `AuthFailed`, `Deferred` to the rest of the system?**
  _216 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.061971830985915494 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 26` to `Community 42`, `Community 12`, `Community 54`, `Community 22`, `Community 59`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `require_web_admin()`) actually correct?**
  _`WebUser` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09588421528720036 - nodes in this community are weakly interconnected._