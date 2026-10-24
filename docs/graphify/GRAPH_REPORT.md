# Graph Report - workspace  (2026-10-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1635 nodes · 4614 edges · 77 communities (54 shown, 23 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 544 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6bfe895f`
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
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 76

## God Nodes (most connected - your core abstractions)
1. `Database` - 227 edges
2. `Settings` - 112 edges
3. `WebUser` - 85 edges
4. `InventoryCollector` - 57 edges
5. `AgentConfig` - 56 edges
6. `_html()` - 49 edges
7. `HardwareInfo` - 43 edges
8. `utc_now()` - 37 edges
9. `InventorySnapshot` - 30 edges
10. `ConfigCli` - 28 edges

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

## Communities (77 total, 23 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (12): admin_delete_device_override(), admin_delete_policy(), admin_set_device_override(), admin_update_policy(), delete_device(), put_device_tags(), try_local_login(), Database (+4 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (38): get_data_key(), get_db(), get_session_secret(), require_web_user(), encrypt_secret(), cookie_secure_for_request(), set_csrf_cookie(), normalize_chassis_type() (+30 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (28): client_ip(), enroll_cleartext_blocked(), request_is_cleartext(), sensitive_over_http_blocked(), tls_mode_http(), https_first_status(), _secret_source(), secrets_status() (+20 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (30): device_silence_status(), effective_stale_after_seconds(), health_snippet(), parse_utc(), build_attention_queue(), build_bootstrap_checklist(), build_bootstrap_progress(), build_config_winner() (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.10
Nodes (35): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate() (+27 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (36): apply_request_path(), apply_status_path(), check_updates(), current_meta_path(), ensure_releases_layout(), _gh_request(), github_token(), list_remote_branches() (+28 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (9): InventoryCollector, CollectorError, Error, Section, SecurityInfo, Antivirus, SecureBoot, TpmPresent (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (32): current_web_user(), require_web_admin(), Settings, dump_session(), load_session(), WebUser, device_archive(), _device_config_context() (+24 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (44): defaults, outputs, runs-on, steps, run, CODE_SIGN_PFX_BASE64, CODE_SIGN_PFX_PASSWORD, CODE_SIGN_TIMESTAMP_URL (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (32): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatActions, Inventory, UpdateCheck, HeartbeatServerResponse (+24 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (31): https_panel_url(), read_domain_from_env(), _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), dashboard_page() (+23 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (19): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), _inventory_mail_digest_loop(), lifespan(), _retention_prune_loop(), _run_bg_cycle() (+11 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (3): ConfigCli, EditableKeys, WindowsElevation

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (16): _badge_html(), build_alert_email(), build_hardware_email(), build_inventory_digest_email(), _dispatch(), dump_notify_flags(), event_visual(), filter_events_for_mail() (+8 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (28): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode, HardwareInfo, BaseboardSerial (+20 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (8): delete_msi_version(), effective_settings_for_device(), ops_update_signals(), prune_old_msi_versions(), versions_pinned_in_config(), admin_agent_update_delete(), agent_update_msi(), _enrollment_msi_name()

### Community 20 - "Community 20"
Cohesion: 0.19
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (3): AgentUpdater, UpdatePathUtil, VersionUtil

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (23): AntivirusProductInfo, Name, ProductState, CpuInfo, Cores, Logical, Name, DiskInfo (+15 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (10): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), settings_from_row() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (23): defaults, runs-on, steps, run, jobs, agent, server, name (+15 more)

### Community 27 - "Community 27"
Cohesion: 0.16
Nodes (12): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+4 more)

### Community 28 - "Community 28"
Cohesion: 0.10
Nodes (16): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, LastBootAt, Os, PendingReboot (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (7): CompatConnection, connect_postgres(), _split_sql_statements(), event_importance(), event_passes_importance(), importance_rank(), types_at_least()

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (12): sanitize_update_target(), check_update(), effective_update_target_for_device(), ingest_uploaded_msi(), is_newer(), resolve_target_cached(), parse_semver(), resolve_target_msi() (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.16
Nodes (10): sanitize_conditions(), AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest (+2 more)

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (15): _as_dict(), _as_list(), _av_name_set(), _bugcheck_code(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _minidump_files_by_name() (+7 more)

### Community 33 - "Community 33"
Cohesion: 0.18
Nodes (9): _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets, _request_json(), safe_msi_filename() (+1 more)

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (13): MinidumpFileInfo, BugcheckCode, BugcheckMessage, BugcheckParameters, ModifiedAt, Name, SizeBytes, MinidumpInfo (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.19
Nodes (7): HeavySectionCache, InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 37 - "Community 37"
Cohesion: 0.21
Nodes (8): enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 38 - "Community 38"
Cohesion: 0.27
Nodes (8): admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), api_key_lookup(), constant_time_equals(), extract_bearer(), verify_secret()

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (6): _fernet_from_key(), generate_session_secret(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (15): archive_current_slot(), download_and_fill_slot(), download_tarball(), ensure_dirs(), fail(), github_token(), promote_slot(), prune_slots() (+7 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (10): authenticate_web_user(), load_ldap_view(), try_ldap_login(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test(), LdapFormData (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 50 - "Community 50"
Cohesion: 0.27
Nodes (6): heartbeat(), clear_refresh_meta_patch(), heartbeat_actions_for_refresh(), _parse_utc_iso(), refresh_request_pending(), set_device_refresh_request()

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 55 - "Community 55"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 56 - "Community 56"
Cohesion: 0.25
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 58 - "Community 58"
Cohesion: 0.22
Nodes (6): _clear_session_cookie(), devices_bulk(), _back(), _devices_redirect_with_flash(), logout(), _maybe_admin_audit()

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 60 - "Community 60"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 62 - "Community 62"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 64 - "Community 64"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 66 - "Community 66"
Cohesion: 0.60
Nodes (5): apply(), formatLocal(), formatRelative(), pad2(), pluralRu()

### Community 67 - "Community 67"
Cohesion: 0.53
Nodes (5): debounce(), initDebouncedForms(), initDeviceLiveSearch(), clear(), render()

### Community 69 - "Community 69"
Cohesion: 0.40
Nodes (4): parse_site_stale_seconds(), _invalidate_fleet_snapshot_cache(), _retention_context(), retention_settings_save()

## Knowledge Gaps
- **210 isolated node(s):** `Keys`, `ServerUrl`, `Settings`, `Inventory`, `UpdateCheck` (+205 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 528 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 20` to `Community 34`, `Community 42`, `Community 11`, `Community 21`, `Community 22`, `Community 57`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 129 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 129 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Keys`, `ServerUrl`, `Settings` to the rest of the system?**
  _210 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 10`, `Community 12`, `Community 14`, `Community 15`, `Community 17`, `Community 19`, `Community 29`, `Community 30`, `Community 37`, `Community 38`, `Community 43`, `Community 50`, `Community 58`, `Community 62`, `Community 69`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 99 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05323653962492438 - nodes in this community are weakly interconnected._