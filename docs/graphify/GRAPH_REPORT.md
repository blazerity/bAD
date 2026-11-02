# Graph Report - workspace  (2026-11-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1990 nodes · 5706 edges · 109 communities (73 shown, 36 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 661 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0b92a91a`
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
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 107

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

## Communities (109 total, 36 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (10): admin_create_policy(), admin_get_policy(), admin_set_device_override(), admin_update_policy(), put_device_tags(), seed_default_admin(), try_local_login(), Database (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (37): admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token() (+29 more)

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (38): admin_server_update_set_branch(), backup_keys_status(), Settings, releases_dir(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run() (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (24): enrollment_rotation_signals(), enrollment_status(), event_importance(), sensitive_over_http_blocked(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), enrich_overview_ops_signals() (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (32): effective_stale_after_seconds(), parse_site_stale_seconds(), format_logged_on_display(), normalize_wave_filter(), event_visual(), _attach_duplicate_signals(), _chassis_map_for_devices(), _chassis_type_from_device() (+24 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (27): device_silence_status(), health_snippet(), parse_utc(), importance_rank(), types_at_least(), _accumulate_hw_bars(), aggregate_incident_feed(), build_config_winner() (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (24): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (24): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), https_panel_url() (+16 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (17): sanitize_update_target(), check_update(), delete_msi_version(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), resolve_target_cached() (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (27): admin_agent_config_defaults(), admin_agent_update_sync(), admin_agent_update_upload(), admin_enrollment_rotate(), admin_list_policies(), admin_security_status(), admin_server_update_apply_status(), admin_server_update_branches() (+19 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (30): require_web_admin(), device_panel_href(), dump_session(), load_session(), WebUser, resolve_device_ref(), _clear_session_cookie(), device_archive() (+22 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (8): AgentUpdater, UpdateAction, Downgrade, None, Upgrade, UpdatePlan, UpdatePathUtil, VersionUtil

### Community 17 - "Community 17"
Cohesion: 0.06
Nodes (34): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, DiskInfo, InterfaceType (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (32): CpuInfo, Cores, Logical, Name, GpuInfo, AdapterRamBytes, DriverVersion, Name (+24 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (4): AssemblyProbe, DeviceIdentity, WmiHelper, BadAgent

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (17): ensure_bad_id_key(), connect_postgres(), apply_user_presence_patch(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index(), ensure_trgm_search_indexes(), index_exists() (+9 more)

### Community 22 - "Community 22"
Cohesion: 0.20
Nodes (22): normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key() (+14 more)

### Community 23 - "Community 23"
Cohesion: 0.18
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (20): HeartbeatActions, Inventory, Uninstall, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse (+12 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (18): default_digest_weekdays(), digest_schedule_preview_ru(), digest_send_due(), digest_slot_hours(), dump_notify_flags(), filter_events_for_mail(), _finalize_digest_send(), flush_inventory_mail_digest() (+10 more)

### Community 26 - "Community 26"
Cohesion: 0.12
Nodes (4): HardwareMaps, MsftPhysicalDiskRow, Serial, UniqueId

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (18): enroll(), rotate_device_key(), approve(), _clean_name(), create_request(), integration_from_token(), is_integration_id(), list_integrations() (+10 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (16): _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label(), disk_role(), format_cpu_short(), _intel_core_i_family(), _intel_family() (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (14): ingest_uploaded_msi(), parse_semver(), _semver_equal(), version_from_msi_name(), sort_key(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir() (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.21
Nodes (14): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle() (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (14): meta_search_haystack(), normalize_logged_on_list(), normalize_search_serial(), device_match_label(), device_search_meta_line(), event_match_label(), highlight_match(), matched_serial_subtitle() (+6 more)

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.22
Nodes (13): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), _parse_utc_iso(), request_device_uninstall() (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (12): collect_hardware_serials(), _add(), enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), disk_bucket_from_fixed_bytes(), format_ram_ddr(), format_ram_gib() (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 39 - "Community 39"
Cohesion: 0.23
Nodes (9): backup_filename(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup(), run_pg_dump() (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (7): _read_server_version(), _add_file(), build_key_escrow_archive(), build_site_bundle(), _dedupe_paths(), _utc_stamp(), _write_json_member()

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (7): admin_device_config(), heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), mark_uninstall_sent_patch()

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 44 - "Community 44"
Cohesion: 0.17
Nodes (11): authenticate_web_user(), ensure_bootstrap_secrets(), _persist(), get_db(), load_ldap_view(), _read_secret_file(), try_ldap_login(), _write_secret_file() (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.24
Nodes (13): bindRangeTabs(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize(), parseJson() (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 50 - "Community 50"
Cohesion: 0.17
Nodes (7): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _dispatch(), _polarity_marker_html(), send_email()

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.16
Nodes (4): SlidingWindowRateLimiter, build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 53 - "Community 53"
Cohesion: 0.18
Nodes (10): current_web_user(), get_data_key(), get_session_secret(), require_web_user(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+2 more)

### Community 54 - "Community 54"
Cohesion: 0.14
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 55 - "Community 55"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.21
Nodes (6): create_integration_request(), _integration_http_error(), poll_integration_request(), client_ip(), IntegrationError, poll_request()

### Community 58 - "Community 58"
Cohesion: 0.24
Nodes (6): enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (10): _apply_bool_form_fields(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policies_page(), policy_create(), policy_edit_page(), policy_update() (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.24
Nodes (6): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), set_csrf_cookie(), validate_csrf()

### Community 62 - "Community 62"
Cohesion: 0.23
Nodes (7): admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), require_device_reader(), constant_time_equals(), extract_bearer()

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 68 - "Community 68"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 72 - "Community 72"
Cohesion: 0.25
Nodes (8): AntivirusProductInfo, Name, ProductState, SecurityInfo, Antivirus, SecureBoot, TpmPresent, TpmSpecVersion

### Community 73 - "Community 73"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 74 - "Community 74"
Cohesion: 0.36
Nodes (3): _cpu_for(), main(), seed_one()

### Community 75 - "Community 75"
Cohesion: 0.39
Nodes (3): decrypt_secret(), encrypt_secret(), _fernet_from_key()

### Community 76 - "Community 76"
Cohesion: 0.25
Nodes (3): admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 78 - "Community 78"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 79 - "Community 79"
Cohesion: 0.36
Nodes (6): mail_settings_page(), mail_settings_save(), mail_settings_test(), _parse_smtp_form(), _smtp_form_context(), SmtpFormData

### Community 81 - "Community 81"
Cohesion: 0.48
Nodes (6): debounce(), hitRow(), init(), clear(), render(), runSearch()

### Community 84 - "Community 84"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 85 - "Community 85"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 86 - "Community 86"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 88 - "Community 88"
Cohesion: 0.40
Nodes (3): admin_server_update_apply(), _admin_server_update_request(), admin_server_update_rollback()

### Community 89 - "Community 89"
Cohesion: 0.40
Nodes (3): _stale_pass(), notify_device_back_online(), notify_stale_device()

### Community 91 - "Community 91"
Cohesion: 0.60
Nodes (3): debounce(), hitRow(), init()

### Community 92 - "Community 92"
Cohesion: 0.40
Nodes (4): _tls_context(), _tls_html(), tls_settings_page(), tls_settings_upload()

## Knowledge Gaps
- **216 isolated node(s):** `bad-server`, `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware` (+211 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 617 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 10`, `Community 11`, `Community 13`, `Community 15`, `Community 20`, `Community 25`, `Community 27`, `Community 30`, `Community 31`, `Community 33`, `Community 36`, `Community 40`, `Community 41`, `Community 44`, `Community 53`, `Community 56`, `Community 58`, `Community 59`, `Community 62`, `Community 71`, `Community 76`, `Community 77`, `Community 79`?**
  _High betweenness centrality (0.184) - this node is a cross-community bridge._
- **Are the 165 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 165 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `AgentLocalKeys`, `ApiKey` to the rest of the system?**
  _216 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.07532467532467532 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 23` to `Community 69`, `Community 42`, `Community 47`, `Community 16`, `Community 19`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 103 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.12895927601809956 - nodes in this community are weakly interconnected._