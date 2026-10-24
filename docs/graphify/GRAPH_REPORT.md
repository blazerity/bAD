# Graph Report - workspace  (2026-10-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1711 nodes · 4778 edges · 85 communities (61 shown, 24 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 475 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e2c1d569`
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
- Community 83

## God Nodes (most connected - your core abstractions)
1. `Database` - 237 edges
2. `Settings` - 112 edges
3. `WebUser` - 87 edges
4. `InventoryCollector` - 64 edges
5. `AgentConfig` - 54 edges
6. `_html()` - 50 edges
7. `utc_now()` - 37 edges
8. `HardwareInfo` - 31 edges
9. `ConfigCli` - 28 edges
10. `InventorySnapshot` - 28 edges

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

## Communities (85 total, 24 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (34): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle() (+26 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (32): admin_token_valid(), ensure_bootstrap_secrets(), _persist(), load_ldap_view(), _read_secret_file(), require_admin_token(), require_api_key(), require_enrollment_token() (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (51): Settings, cookie_secure_for_request(), WebUser, https_panel_url(), read_domain_from_env(), _backup_context(), backups_key_escrow_download(), backups_settings_page() (+43 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (6): admin_delete_device_override(), list_events(), seed_default_admin(), try_local_login(), Database, utc_now()

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (36): admin_agent_config_defaults(), admin_agent_update_delete(), admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_delete_policy(), admin_device_config() (+28 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (36): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+28 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (29): authenticate_web_user(), get_data_key(), get_db(), get_session_secret(), require_web_admin(), require_web_user(), set_csrf_cookie(), _apply_bool_form_fields() (+21 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (22): effective_stale_after_seconds(), enrollment_rotation_signals(), enrollment_status(), mark_enrollment_wave_done(), sensitive_over_http_blocked(), build_bootstrap_checklist(), build_bootstrap_progress(), normalize_wave_filter() (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (26): format_logged_on_display(), inventory_meta_cache(), meta_search_haystack(), normalize_logged_on_list(), normalize_logged_on_user(), _as_dict(), _as_list(), _av_name_set() (+18 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (23): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), tls_mode_http(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path() (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (18): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), _finalize_digest_send() (+10 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (18): sanitize_update_target(), check_update(), delete_msi_version(), effective_settings_for_device(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), ops_update_signals() (+10 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (5): AgentApiException, IsAuthFailure, BadApiClient, IInventoryCollector, Worker

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (3): AgentUpdater, UpdatePathUtil, VersionUtil

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (9): adapt_sql(), CompatConnection, connect_postgres(), _split_sql_statements(), event_importance(), event_passes_importance(), importance_rank(), types_at_least() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 23 - "Community 23"
Cohesion: 0.12
Nodes (15): device_silence_status(), health_snippet(), parse_site_stale_seconds(), parse_utc(), normalize_chassis_type(), _chassis_type_from_device(), _device_config_context(), device_detail_page() (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.15
Nodes (15): _accumulate_hw_bars(), build_attention_queue(), build_config_winner(), build_dashboard_stats(), build_wave_counts(), device_has_agent_local(), enrich_overview_ops_signals(), _facet_from_device_meta() (+7 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.12
Nodes (11): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+3 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (11): enroll(), inventory(), rotate_device_key(), enrollment_token_file(), mark_device_enrolled(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment() (+3 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (19): HeartbeatActions, Inventory, UpdateCheck, HeartbeatServerResponse, Actions, Config, RemoteAgentConfigResponse, Settings (+11 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (22): HardwareInfo, BaseboardSerial, Battery, BiosManufacturer, BiosReleaseDate, BiosSerial, BiosVersion, ChassisType (+14 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (9): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, InventoryRequest (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (4): set_latest_msi_version(), admin_agent_update_status(), agent_update_msi(), _enrollment_msi_name()

### Community 33 - "Community 33"
Cohesion: 0.20
Nodes (6): AsciiReportWriter, CpuInfo, Cores, Logical, Name, ReportFormat

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (17): CollectorError, Error, Section, InstalledProgram, Name, Publisher, Version, NetworkInfo (+9 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (6): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), set_device_refresh_request()

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (7): ConfigLocalPayload, Keys, ServerUrl, Settings, MsftPhysicalDiskRow, Serial, UniqueId

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (16): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+8 more)

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 40 - "Community 40"
Cohesion: 0.23
Nodes (7): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json()

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (9): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (5): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, PushCli

### Community 44 - "Community 44"
Cohesion: 0.13
Nodes (15): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+7 more)

### Community 45 - "Community 45"
Cohesion: 0.14
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 48 - "Community 48"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 51 - "Community 51"
Cohesion: 0.15
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.18
Nodes (9): event_visual(), event_detail_page(), events_page(), home(), overview_alias(), overview_search_json(), password_page(), settings_home() (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 58 - "Community 58"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 60 - "Community 60"
Cohesion: 0.31
Nodes (7): _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test(), LdapFormData, login_page(), _parse_ldap_form()

### Community 61 - "Community 61"
Cohesion: 0.25
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 62 - "Community 62"
Cohesion: 0.31
Nodes (7): encrypt_secret(), mail_settings_page(), mail_settings_save(), mail_settings_test(), _parse_smtp_form(), _smtp_form_context(), SmtpFormData

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (8): AntivirusProductInfo, Name, ProductState, SecurityInfo, Antivirus, SecureBoot, TpmPresent, TpmSpecVersion

### Community 64 - "Community 64"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 65 - "Community 65"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 66 - "Community 66"
Cohesion: 0.29
Nodes (3): current_web_user(), dump_session(), load_session()

### Community 67 - "Community 67"
Cohesion: 0.32
Nodes (4): debounce(), init(), render(), section()

### Community 68 - "Community 68"
Cohesion: 0.48
Nodes (6): debounce(), init(), clear(), render(), runSearch(), section()

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 70 - "Community 70"
Cohesion: 0.33
Nodes (6): DiskInfo, InterfaceType, MediaType, Model, SerialNumber, SizeBytes

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 72 - "Community 72"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 73 - "Community 73"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 74 - "Community 74"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 76 - "Community 76"
Cohesion: 0.50
Nodes (4): VolumeInfo, FreeBytes, Letter, SizeBytes

## Knowledge Gaps
- **212 isolated node(s):** `AgentLocalKeys`, `ApiKey`, `CollectHardware`, `CollectSoftware`, `CollectUsers` (+207 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 546 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 16` to `Community 25`, `Community 52`, `Community 47`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Are the 131 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 131 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AgentLocalKeys`, `ApiKey`, `CollectHardware` to the rest of the system?**
  _212 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05289450484866295 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 3` to `Community 32`, `Community 0`, `Community 1`, `Community 35`, `Community 4`, `Community 66`, `Community 6`, `Community 2`, `Community 8`, `Community 12`, `Community 60`, `Community 15`, `Community 14`, `Community 19`, `Community 53`, `Community 23`, `Community 28`, `Community 62`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 98 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05541346973572037 - nodes in this community are weakly interconnected._