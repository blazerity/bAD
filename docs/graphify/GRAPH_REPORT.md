# Graph Report - bAD  (2026-11-06)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2192 nodes · 6343 edges · 109 communities (75 shown, 34 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 736 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `83e7655c`
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
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 86
- Community 87
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 106

## God Nodes (most connected - your core abstractions)
1. `Database` - 309 edges
2. `Settings` - 127 edges
3. `WebUser` - 98 edges
4. `post()` - 73 edges
5. `InventoryCollector` - 64 edges
6. `AgentConfig` - 62 edges
7. `_html()` - 54 edges
8. `utc_now()` - 52 edges
9. `HardwareInfo` - 43 edges
10. `BadAgent` - 38 edges

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

## Communities (109 total, 34 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (60): collect_hardware_serials(), _add(), enrich_hardware_meta(), inventory_meta_cache(), meta_search_haystack(), normalize_chassis_type(), normalize_logged_on_user(), normalize_search_serial() (+52 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (36): set_csrf_cookie(), parse_site_stale_seconds(), format_logged_on_display(), normalize_logged_on_list(), highlight_match(), parse_recipients(), _apply_bool_form_fields(), _apply_inventory_overlay() (+28 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (34): event_importance(), importance_rank(), types_at_least(), types_exact_importance(), _accumulate_hw_bars(), aggregate_incident_feed(), _fresh(), build_attention_queue() (+26 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (42): set_latest_msi_version(), admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (46): WebUser, backups_settings_run(), _build_enrollment_msiexec_script(), device_archive(), device_restore(), devices_issue_enrollment_code(), _enrollment_msi_name(), enrollment_rotate() (+38 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (37): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+29 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (28): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _chassis_key(), default_digest_weekdays(), _device_card_html(), digest_schedule_preview_ru() (+20 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (6): AgentApiException, IsAuthFailure, AgentUpdater, BadApiClient, TextLimit, Worker

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (25): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (31): HeartbeatActions, Inventory, Uninstall, UpdateCheck, UploadMinidump, HeartbeatServerResponse, Actions, Config (+23 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 13 - "Community 13"
Cohesion: 0.10
Nodes (26): archive_device(), issue_agent_signing_key(), request_device_refresh_api(), restore_device(), revoke_device(), device_panel_href(), Database, set_device_refresh_request() (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (23): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentCode (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.10
Nodes (22): heartbeat(), health_snippet(), parse_iso(), parse_utc(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), heartbeat_refresh_meta_patch(), refresh_request_pending() (+14 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (19): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+11 more)

### Community 17 - "Community 17"
Cohesion: 0.08
Nodes (17): Settings, effective_stale_after_seconds(), enrollment_rotation_signals(), enrich_overview_ops_signals(), panel_tls_mode(), patch_security_for_qa(), qa_ui_active(), https_first_status() (+9 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.12
Nodes (19): bad_id_for_device(), _encode_crockford(), ensure_bad_id_key(), connect_postgres(), apply_user_presence_patch(), connect_autocommit(), create_index_concurrently(), ensure_devices_bad_id_index() (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (5): BadCli, IInventoryCollector, PushCli, ServerUrlRules, UpdateCli

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (16): backup_filename(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup(), run_pg_dump() (+8 more)

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (4): AsciiReportWriter, HtmlReportWriter, ReportFormat, TimeFormat

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (4): is_newer(), _compact_json(), utc_now(), _finalize_digest_send()

### Community 24 - "Community 24"
Cohesion: 0.12
Nodes (18): enroll(), admin_token_valid(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token() (+10 more)

### Community 25 - "Community 25"
Cohesion: 0.17
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 26 - "Community 26"
Cohesion: 0.09
Nodes (18): authenticate_web_user(), current_web_user(), load_ldap_view(), try_ldap_login(), try_local_login(), cookie_secure_for_request(), dump_session(), load_session() (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (22): create_enrollment_grant(), create_app(), dump_name_ok(), enrollment_code_hash(), generate_token(), new_device_signing_key(), _device_id(), _fingerprint() (+14 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (4): AssemblyProbe, DeviceIdentity, QuietFiles, BadAgent

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (11): delete_msi_version(), ingest_uploaded_msi(), parse_semver(), prune_old_msi_versions(), _semver_equal(), version_from_msi_name(), versions_pinned_in_config(), agent_update_msi() (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (21): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (26): HardwareInfo, BaseboardSerial, Battery, BiosManufacturer, BiosReleaseDate, BiosSerial, BiosVersion, ChassisType (+18 more)

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (14): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.08
Nodes (24): AntivirusProductInfo, Name, ProductState, BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status (+16 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (4): AgentUninstaller, MsiexecLauncher, UninstallCli, WindowsEventLog

### Community 35 - "Community 35"
Cohesion: 0.16
Nodes (17): create_integration_request(), _integration_http_error(), poll_integration_request(), approve(), _clean_name(), create_request(), IntegrationError, is_integration_id() (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.10
Nodes (15): require_web_admin(), device_silence_status(), filter_devices_by_wave(), _match(), normalize_wave_filter(), _attach_duplicate_signals(), _device_freshness_tier(), devices_allow_enrollment_request() (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.16
Nodes (14): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollmentGrantBody, EnrollmentRequestBody, EnrollmentRotateBody, EnrollRequest (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 41 - "Community 41"
Cohesion: 0.16
Nodes (10): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), _cpu_for() (+2 more)

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (4): AgentSigningKey, KeyPath, SkipFetchPath, SigningKeyFetchResult

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (7): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (9): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token() (+1 more)

### Community 47 - "Community 47"
Cohesion: 0.15
Nodes (12): backup_keys_status(), sensitive_over_http_blocked(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_site_bundle_download(), home(), integrations_settings_page() (+4 more)

### Community 48 - "Community 48"
Cohesion: 0.12
Nodes (14): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+6 more)

### Community 50 - "Community 50"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (9): agent_minidump(), _copy_minidump(), cause_label(), cause_text(), _from_parsed(), _module_for_address(), _module_name(), read_header() (+1 more)

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (8): _accepted_inventory(), admin_enrollment_rotate(), agent_report_html(), _display_serial(), _enforce_enroll_rate(), inventory(), submit_enrollment_request(), InventoryRequest

### Community 54 - "Community 54"
Cohesion: 0.20
Nodes (8): enrollment_status(), enrollment_token_file(), mark_device_enrolled(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 56 - "Community 56"
Cohesion: 0.23
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 57 - "Community 57"
Cohesion: 0.23
Nodes (7): sanitize_update_target(), check_update(), effective_settings_for_device(), effective_update_target_for_device(), ops_update_signals(), resolve_target_cached(), resolve_target_msi()

### Community 59 - "Community 59"
Cohesion: 0.18
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 61 - "Community 61"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 63 - "Community 63"
Cohesion: 0.38
Nodes (3): DetachedProcessStart, ProcessInformation, StartupInfo

### Community 65 - "Community 65"
Cohesion: 0.29
Nodes (4): decrypt_secret(), encrypt_secret(), _fernet_from_key(), generate_data_key()

### Community 66 - "Community 66"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 67 - "Community 67"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

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
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 73 - "Community 73"
Cohesion: 0.38
Nodes (3): MinidumpHeartbeatUpload, MinidumpUploadHelper, MinidumpUploadResolveResult

### Community 74 - "Community 74"
Cohesion: 0.43
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 75 - "Community 75"
Cohesion: 0.33
Nodes (3): init(), render(), section()

### Community 76 - "Community 76"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 78 - "Community 78"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 80 - "Community 80"
Cohesion: 0.53
Nodes (5): hitRow(), init(), clear(), render(), runSearch()

### Community 81 - "Community 81"
Cohesion: 0.40
Nodes (3): initDeviceLiveSearch(), clear(), render()

### Community 82 - "Community 82"
Cohesion: 0.33
Nodes (3): _accept_policy(), PolicyFormData, _validate_update_target_pin()

### Community 87 - "Community 87"
Cohesion: 0.60
Nodes (4): init(), apply(), applyChart(), applyProblems()

### Community 93 - "Community 93"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

## Knowledge Gaps
- **222 isolated node(s):** `bad-server`, `Inventory`, `Uninstall`, `UpdateCheck`, `UploadMinidump` (+217 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 669 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Community 13` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 10`, `Community 15`, `Community 16`, `Community 17`, `Community 19`, `Community 21`, `Community 23`, `Community 24`, `Community 26`, `Community 27`, `Community 29`, `Community 35`, `Community 36`, `Community 46`, `Community 47`, `Community 52`, `Community 53`, `Community 54`, `Community 57`, `Community 68`, `Community 79`, `Community 82`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Are the 181 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 181 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `Inventory`, `Uninstall` to the rest of the system?**
  _222 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05101807366735301 - nodes in this community are weakly interconnected._
- **Why does `Worker` connect `Community 7` to `Community 11`, `Community 28`, `Community 20`, `Community 22`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 111 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 111 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.04195804195804196 - nodes in this community are weakly interconnected._