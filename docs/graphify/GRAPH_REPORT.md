# Graph Report - bAD  (2026-11-04)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1995 nodes · 5721 edges · 103 communities (73 shown, 30 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 661 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bc276ddf`
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
- Community 96
- Community 97
- Community 101

## God Nodes (most connected - your core abstractions)
1. `Database` - 279 edges
2. `Settings` - 119 edges
3. `WebUser` - 92 edges
4. `InventoryCollector` - 64 edges
5. `post()` - 64 edges
6. `AgentConfig` - 56 edges
7. `_html()` - 53 edges
8. `utc_now()` - 45 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 33 edges

## Surprising Connections (you probably didn't know these)
- `require_web_user()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/sessions.py
- `device_archive()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py
- `_device_config_context()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py
- `device_config_override_save()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py
- `device_delete()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py

## Import Cycles
- None detected.

## Communities (103 total, 30 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (73): authenticate_web_user(), require_web_admin(), cookie_secure_for_request(), releases_dir(), WebUser, https_panel_url(), read_domain_from_env(), _backup_context() (+65 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (13): try_local_login(), Database, _assign_bad_ids(), _rewrite_bad_ids(), _attach_duplicate_signals(), devices_csv_export(), _devices_wave_context(), events_page() (+5 more)

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (41): admin_server_update_set_token(), utc_now(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request() (+33 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (19): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), adapt_sql(), CompatConnection, CompatCursor, connect_postgres(), _split_sql_statements() (+11 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (37): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_delete_device_override() (+29 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (23): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (22): event_importance(), aggregate_incident_feed(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_wave_counts(), device_has_agent_local(), enrich_overview_ops_signals() (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (17): admin_server_update_apply(), _admin_server_update_request(), admin_server_update_rollback(), Settings, enrollment_rotation_signals(), enrollment_status(), mark_enrollment_wave_done(), sensitive_over_http_blocked() (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (17): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (4): AgentUpdater, MsiexecLauncher, UpdatePathUtil, VersionUtil

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (26): archive_device(), request_device_refresh_api(), restore_device(), revoke_device(), device_panel_href(), set_device_refresh_request(), resolve_device_ref(), _apply_bool_form_fields() (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (32): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, HardwareInfo, BaseboardSerial (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (19): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value() (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (4): AssemblyProbe, DeviceIdentity, WmiHelper, BadAgent

### Community 19 - "Community 19"
Cohesion: 0.07
Nodes (26): AntivirusProductInfo, Name, ProductState, CpuInfo, Cores, Logical, Name, GpuInfo (+18 more)

### Community 20 - "Community 20"
Cohesion: 0.12
Nodes (16): collect_hardware_serials(), _add(), meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line(), event_match_label() (+8 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (15): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _device_card_html(), _dispatch(), _event_row_html() (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (21): create_integration_request(), enroll(), _integration_http_error(), poll_integration_request(), rotate_device_key(), get_db(), approve(), _clean_name() (+13 more)

### Community 23 - "Community 23"
Cohesion: 0.20
Nodes (22): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key() (+14 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (11): HeavySectionCache, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InstalledProgram, Name, Publisher (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.08
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (18): importance_rank(), types_at_least(), _accumulate_hw_bars(), build_config_winner(), build_dashboard_stats(), _hbar_block(), chart_filter_href(), cpu_family_bucket() (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.09
Nodes (15): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId, DiskInfo (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (12): load_ldap_view(), try_ldap_login(), authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn() (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 31 - "Community 31"
Cohesion: 0.14
Nodes (12): sanitize_update_target(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), ops_update_signals(), resolve_target_cached(), prune_old_msi_versions(), set_latest_msi_version() (+4 more)

### Community 32 - "Community 32"
Cohesion: 0.20
Nodes (14): _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (14): _amd_family(), _core_i_generation(), disk_bucket_from_fixed_bytes(), disk_role(), format_cpu_short(), _intel_core_i_family(), _intel_family(), meta_facet_matches() (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (14): apply_user_presence_patch(), enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), cpu_family_label(), cpu_vendor_label(), format_ram_ddr(), format_ram_gib() (+6 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (3): AgentUninstaller, UninstallCli, WindowsEventLog

### Community 37 - "Community 37"
Cohesion: 0.19
Nodes (10): admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), integration_from_token(), require_device_reader(), api_key_lookup(), constant_time_equals() (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.17
Nodes (11): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, IntegrationLookupBody (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (6): enrollment_token_file(), mark_device_enrolled(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 43 - "Community 43"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 46 - "Community 46"
Cohesion: 0.12
Nodes (16): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+8 more)

### Community 47 - "Community 47"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (4): delete_msi_version(), resolve_target_msi(), agent_update_msi(), _enrollment_msi_name()

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (8): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename()

### Community 50 - "Community 50"
Cohesion: 0.22
Nodes (11): digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours(), filter_events_for_mail(), flush_inventory_mail_digest(), flush_mail_digest(), _mail_digest_enabled(), _mail_group_from_device() (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.18
Nodes (6): device_silence_status(), effective_stale_after_seconds(), health_snippet(), parse_site_stale_seconds(), parse_utc(), _device_freshness_tier()

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (4): SlidingWindowRateLimiter, build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.17
Nodes (6): current_web_user(), get_data_key(), get_session_secret(), require_web_user(), dump_session(), load_session()

### Community 60 - "Community 60"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (5): decrypt_secret(), encrypt_secret(), _fernet_from_key(), generate_data_key(), generate_session_secret()

### Community 62 - "Community 62"
Cohesion: 0.25
Nodes (5): ensure_csrf(), get_csrf_token(), new_csrf_token(), set_csrf_cookie(), validate_csrf()

### Community 63 - "Community 63"
Cohesion: 0.20
Nodes (5): check_update(), is_newer(), parse_semver(), _semver_equal(), sort_key()

### Community 64 - "Community 64"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 66 - "Community 66"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.22
Nodes (7): format_logged_on_display(), _device_inventory_nav(), _disk_overview_line(), _enrich_device_row(), _format_bytes(), _format_chassis(), _format_os()

### Community 68 - "Community 68"
Cohesion: 0.27
Nodes (8): default_digest_weekdays(), dump_notify_flags(), parse_recipients(), mail_settings_save(), mail_settings_test(), _parse_smtp_form(), _smtp_form_context(), SmtpFormData

### Community 69 - "Community 69"
Cohesion: 0.22
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 71 - "Community 71"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 72 - "Community 72"
Cohesion: 0.29
Nodes (4): _stale_pass(), notify_device_back_online(), notify_enroll(), notify_stale_device()

### Community 73 - "Community 73"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 74 - "Community 74"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 75 - "Community 75"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 76 - "Community 76"
Cohesion: 0.43
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 78 - "Community 78"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 79 - "Community 79"
Cohesion: 0.47
Nodes (4): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file()

### Community 80 - "Community 80"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 83 - "Community 83"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

## Knowledge Gaps
- **216 isolated node(s):** `bad-server`, `EditableKeys`, `ChargePercent`, `EstimatedRuntimeMinutes`, `Name` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 618 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 1` to `Community 0`, `Community 3`, `Community 4`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 17`, `Community 20`, `Community 21`, `Community 22`, `Community 29`, `Community 31`, `Community 32`, `Community 35`, `Community 37`, `Community 42`, `Community 48`, `Community 54`, `Community 58`, `Community 63`, `Community 68`, `Community 72`, `Community 79`, `Community 87`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 165 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 165 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `EditableKeys`, `ChargePercent` to the rest of the system?**
  _216 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0696763553906411 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 24` to `Community 39`, `Community 40`, `Community 44`, `Community 13`, `Community 18`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 103 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.054871220604703244 - nodes in this community are weakly interconnected._