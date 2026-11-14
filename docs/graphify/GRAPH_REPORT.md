# Graph Report - bAD  (2026-11-14)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2488 nodes · 7989 edges · 103 communities (78 shown, 25 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 617 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6c78ccc8`
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
- Community 93
- Community 94
- Community 95
- Community 96
- Community 102

## God Nodes (most connected - your core abstractions)
1. `Database` - 231 edges
2. `Settings` - 125 edges
3. `WebUser` - 108 edges
4. `AgentConfig` - 69 edges
5. `InventoryCollector` - 65 edges
6. `_html()` - 61 edges
7. `utc_now()` - 54 edges
8. `BadAgent` - 46 edges
9. `HardwareInfo` - 43 edges
10. `DbPanelSettingsMixin` - 40 edges

## Surprising Connections (you probably didn't know these)
- `admin_create_policy()` --uses--> `AgentPolicyBody`  [INFERRED]
  server/bad_server/api.py → server/bad_server/schemas.py
- `submit_enrollment_request()` --uses--> `EnrollmentRequestBody`  [INFERRED]
  server/bad_server/api.py → server/bad_server/schemas.py
- `enroll()` --uses--> `EnrollRequest`  [INFERRED]
  server/bad_server/api.py → server/bad_server/schemas.py
- `enroll()` --uses--> `EnrollResponse`  [INFERRED]
  server/bad_server/api.py → server/bad_server/schemas.py
- `heartbeat()` --uses--> `HeartbeatRequest`  [INFERRED]
  server/bad_server/api.py → server/bad_server/schemas.py

## Import Cycles
- 2-file cycle: `server/bad_server/db.py -> server/bad_server/db_panel_settings.py -> server/bad_server/db.py`
- 2-file cycle: `server/bad_server/db.py -> server/bad_server/db_devices.py -> server/bad_server/db.py`
- 2-file cycle: `server/bad_server/db.py -> server/bad_server/db_ingest.py -> server/bad_server/db.py`
- 2-file cycle: `server/bad_server/db.py -> server/bad_server/db_identity.py -> server/bad_server/db.py`
- 2-file cycle: `server/bad_server/db.py -> server/bad_server/db_events.py -> server/bad_server/db.py`

## Communities (103 total, 25 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (42): delete_msi_version(), set_latest_msi_version(), authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), load_ldap_view() (+34 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (53): ops_update_signals(), badge_recent_after_seconds(), device_silence_status(), effective_recent_after_seconds(), effective_stale_after_seconds(), health_snippet(), parse_iso(), parse_site_recent_seconds() (+45 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (31): encrypt_zip(), main(), new_password(), pack_publish(), zip_directory(), compute_effective_config(), condition_matches(), config_version() (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (30): compute_setting_sources(), event_importance(), aggregate_incident_feed(), _fresh(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner() (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (7): AgentApiException, IsAuthFailure, IsBoardChanged, BadApiClient, EnrollResult, InventoryPostFailure, Worker

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (12): CliLine, CliOutcome, ExitCode, Html, KeyRejected, Lines, StopAfterReply, Tail (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (30): enroll(), _integration_http_error(), poll_integration_request(), require_api_key(), try_local_login(), approve(), _clean_name(), create_request() (+22 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (33): build_hardware_email(), build_inventory_digest_email(), _chassis_key(), _compact_event_html(), default_digest_weekdays(), _device_card_html(), digest_schedule_preview_ru(), digest_send_due() (+25 more)

### Community 8 - "Community 8"
Cohesion: 0.07
Nodes (25): AgentConfig, AgentLocalKeys, ApiKey, BadId, CollectHardware, CollectSoftware, CollectUsers, EnrollmentCode (+17 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 10 - "Community 10"
Cohesion: 0.06
Nodes (7): AgentArchive, SigningKeyFetchResult, DeviceIdentity, QuietFiles, TextLimit, WmiHelper, BadAgent

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (36): admin_server_update_set_token(), apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token() (+28 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (3): DbPanelSettingsMixin, sort_key(), utc_now()

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (23): OfflineFlushResult, AuthException, AuthFailed, BoardChanged, Deferred, Error, Failures, NextRetryUtc (+15 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (38): _as_dict(), _as_list(), _av_name_set(), _bag_delta(), _bios_token(), _both_lists(), _bugcheck_code(), _cpu_label() (+30 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (23): _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle(), _sleep_interval() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (27): apply_user_presence_patch(), enrich_hardware_meta(), inventory_meta_cache(), normalize_chassis_type(), _amd_family(), _core_i_generation(), cpu_family_label(), cpu_vendor_label() (+19 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (34): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_get_policy() (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (25): admin_agent_update_delete(), admin_delete_device_override(), admin_delete_policy(), admin_set_device_override(), admin_update_policy(), agent_link_progress(), create_enrollment_grant(), create_integration_request() (+17 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (19): UpdateAction, Downgrade, None, Upgrade, UpdateCheckResponse, Action, ArchivePassword, ArchiveSha256 (+11 more)

### Community 21 - "Community 21"
Cohesion: 0.10
Nodes (28): bad_id_from_board(), ensure_bad_id_key(), normalize_machine_guid(), random_bad_id(), constant_time_equals(), _approved_enrollment_rows(), _archive_device(), _current_arc_size() (+20 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (33): Settings, WebUser, _see_other(), backups_settings_run(), general_settings_save(), _inventory_signature_flag(), mail_settings_save(), policy_delete() (+25 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (12): is_bad_id(), CompatConnection, connect_postgres(), _split_sql_statements(), _compact_json(), _utc_cutoff(), _utc_iso(), connect_autocommit() (+4 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (19): admin_token_valid(), require_admin_token(), Database, _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_site_bundle_download(), _commit_retention() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (20): enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z() (+12 more)

### Community 26 - "Community 26"
Cohesion: 0.06
Nodes (31): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatActions, Inventory, Uninstall, UpdateCheck (+23 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (4): AsciiReportWriter, HtmlReportWriter, ReportFormat, TimeFormat

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (32): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, HardwareInfo, BaseboardSerial (+24 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (15): backup_filename(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup(), run_pg_dump() (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (14): format_logged_on_display(), meta_search_haystack(), normalize_logged_on_list(), normalize_logged_on_user(), panel_root(), _read_server_version(), _format_config_interval(), _pager_items() (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.11
Nodes (18): all_same(), b64_32(), clean_serial(), clean_uuid(), core_version(), decompress_product_code(), fingerprint_hex(), is_placeholder() (+10 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (11): HeavySectionCache, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InstalledProgram, Name, Publisher (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.07
Nodes (26): AntivirusProductInfo, Name, ProductState, CpuInfo, Cores, Logical, Name, GpuInfo (+18 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (16): collect_hardware_serials(), _add(), normalize_search_serial(), device_match_label(), device_match_parts(), device_search_meta_line(), event_match_label(), _first_folded_hit() (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (11): _accepted_inventory(), agent_report_html(), _display_serial(), _enforce_enroll_rate(), _enrollment_proof_bytes(), inventory(), _log_inventory_signature(), _snapshot_smbios_uuid() (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (4): CliColumns, ServiceCli, UninstallCli, WindowsElevation

### Community 40 - "Community 40"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (6): client_ip(), sensitive_over_http_blocked(), https_first_status(), _secret_source(), secrets_status(), security_status()

### Community 42 - "Community 42"
Cohesion: 0.22
Nodes (22): esc(), init(), appendExpandedPage(), clearExpandedFeed(), clearShort(), deviceExpandedRow(), deviceShortRow(), eventExpandedRow() (+14 more)

### Community 43 - "Community 43"
Cohesion: 0.17
Nodes (3): AgentUninstaller, MsiexecLauncher, WindowsEventLog

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.19
Nodes (19): apply_archive(), decrypt_arc(), download_file(), file_exists(), file_len(), header_u64(), hex_eq(), http_call() (+11 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (6): DetachedProcessStart, ProcessInformation, StartupInfo, EnrollmentProof, ProofPath, SecurityAttributes

### Community 48 - "Community 48"
Cohesion: 0.14
Nodes (5): InvalidKeyReset, ServerUrlRules, LinkProbe, LinkProbeStatus, ReportRelay

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (4): AgentSigningKey, KeyPath, SkipFetchPath, InventorySignTrace

### Community 50 - "Community 50"
Cohesion: 0.21
Nodes (13): append_quoted(), computer_name(), file_exists(), json_string(), main(), print_field(), print_info(), read_hostname() (+5 more)

### Community 51 - "Community 51"
Cohesion: 0.12
Nodes (11): check_update(), resolve_target_msi(), agent_update_archive(), agent_update_check(), heartbeat(), _range_start(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh() (+3 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (12): cancel_device_uninstall(), clear_uninstall_request_patch(), device_uninstall_confirm_value(), expire_uninstall_request_if_needed(), heartbeat_should_send_uninstall(), _now(), request_device_uninstall(), start_new_uninstall_request_patch() (+4 more)

### Community 54 - "Community 54"
Cohesion: 0.16
Nodes (3): DoctorCli, PushCli, UpdateCli

### Community 55 - "Community 55"
Cohesion: 0.30
Nodes (18): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), init_bad_python(), promote_slot() (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (15): bindRangeTabs(), currentChartSevFilter(), fmtDay(), init(), layoutFew(), layoutSquarified(), niceMax(), onResize() (+7 more)

### Community 57 - "Community 57"
Cohesion: 0.16
Nodes (11): event_detail_page(), events_page(), _html(), login_page(), login_submit(), password_page(), password_submit(), render() (+3 more)

### Community 58 - "Community 58"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 59 - "Community 59"
Cohesion: 0.14
Nodes (10): config_local_from_meta(), _parse_bool(), provenance_from_effective(), sanitize_conditions(), sanitize_settings(), sanitize_update_target(), resolve_target_cached(), _apply_bool_form_fields() (+2 more)

### Community 60 - "Community 60"
Cohesion: 0.19
Nodes (4): DbEventsMixin, importance_rank(), types_at_least(), types_exact_importance()

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (15): BadAgent, net8.0, BouncyCastle.Cryptography (2.5.1), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0) (+7 more)

### Community 62 - "Community 62"
Cohesion: 0.12
Nodes (17): InventorySnapshot, AgentVersion, BadId, CollectedAt, CollectorErrors, Hardware, Host, Minidumps (+9 more)

### Community 64 - "Community 64"
Cohesion: 0.12
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 67 - "Community 67"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 68 - "Community 68"
Cohesion: 0.25
Nodes (11): applyRow(), buildRow(), esc(), findMainTbody(), flashNewRows(), init(), applyPayload(), tick() (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 72 - "Community 72"
Cohesion: 0.29
Nodes (11): ensure_dir(), ensure_server_url(), json_escape(), retarget_service(), save_secrets(), spawn_restarter(), stopped(), wide_to_utf8() (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 74 - "Community 74"
Cohesion: 0.27
Nodes (9): arg_is_cleanup(), delete_tree(), join_child(), paths_equal(), restart_service(), sweep_old_tails(), sweep_temp_names(), trim_trailing_slash() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.24
Nodes (6): computer_name(), handler(), read_hostname(), report(), ServiceMain(), wait_ms()

### Community 76 - "Community 76"
Cohesion: 0.58
Nodes (9): applyLayout(), backdrop(), init(), isMobile(), onToggleClick(), readDesktopCollapsed(), setDesktopCollapsed(), setMobileOpen() (+1 more)

### Community 77 - "Community 77"
Cohesion: 0.25
Nodes (8): DiskInfo, InterfaceType, MediaType, Model, PnpDeviceId, Removable, SerialNumber, SizeBytes

### Community 78 - "Community 78"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 79 - "Community 79"
Cohesion: 0.32
Nodes (5): _accept_policy(), policy_create(), policy_update(), PolicyFormData, _validate_update_target_pin()

### Community 80 - "Community 80"
Cohesion: 0.57
Nodes (6): apply(), formatClock(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 81 - "Community 81"
Cohesion: 0.43
Nodes (5): _ldap_form_context(), ldap_settings_save(), ldap_settings_test(), LdapFormData, _parse_ldap_form()

### Community 82 - "Community 82"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 83 - "Community 83"
Cohesion: 0.53
Nodes (3): build_server_runtime(), _probe_database(), _process_memory_bytes()

### Community 87 - "Community 87"
Cohesion: 0.50
Nodes (5): config_server(), hex_nibble(), json_string(), load_saved_keys(), read_text()

### Community 89 - "Community 89"
Cohesion: 0.60
Nodes (4): chartNote(), init(), apply(), applyChart()

### Community 92 - "Community 92"
Cohesion: 1.00
Nodes (3): init(), scan(), scrollActive()

### Community 95 - "Community 95"
Cohesion: 0.67
Nodes (3): MsftPhysicalDiskRow, Serial, UniqueId

## Knowledge Gaps
- **235 isolated node(s):** `bad-server`, `AuthException`, `AuthFailed`, `BoardChanged`, `Deferred` (+230 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 690 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 4` to `Community 65`, `Community 37`, `Community 8`, `Community 10`, `Community 48`, `Community 23`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 178 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 178 INFERRED edges - model-reasoned connections that need verification._
- **What connects `bad-server`, `AuthException`, `AuthFailed` to the rest of the system?**
  _235 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06155950752393981 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 24` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 6`, `Community 7`, `Community 12`, `Community 14`, `Community 15`, `Community 18`, `Community 19`, `Community 21`, `Community 22`, `Community 23`, `Community 28`, `Community 30`, `Community 31`, `Community 35`, `Community 36`, `Community 38`, `Community 41`, `Community 51`, `Community 52`, `Community 53`, `Community 57`, `Community 60`, `Community 63`, `Community 79`, `Community 81`, `Community 93`, `Community 94`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 105 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 105 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05171907140758154 - nodes in this community are weakly interconnected._