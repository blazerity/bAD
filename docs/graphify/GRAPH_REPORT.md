# Graph Report - bAD  (2026-10-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1192 nodes · 3323 edges · 71 communities (49 shown, 22 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 415 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ee0fd16b`
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
- Community 55
- Community 56
- Community 57
- Community 58
- Community 60
- Community 61
- Community 62
- Community 63
- Community 65
- Community 66
- Community 70

## God Nodes (most connected - your core abstractions)
1. `Database` - 185 edges
2. `Settings` - 69 edges
3. `WebUser` - 67 edges
4. `AgentConfig` - 52 edges
5. `_html()` - 46 edges
6. `HardwareInfo` - 35 edges
7. `InventoryCollector` - 31 edges
8. `ConfigCli` - 28 edges
9. `InventorySnapshot` - 28 edges
10. `utc_now()` - 26 edges

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

## Communities (71 total, 22 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (18): Settings, enrollment_rotation_signals(), enrollment_status(), enrollment_token_file(), mark_enrollment_wave_done(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment() (+10 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (22): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (6): AsciiReportWriter, BadCli, HtmlReportWriter, IInventoryCollector, ReportFormat, ReportPathResolver

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (22): AgentConfig, AgentLocalKeys, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken (+14 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (4): enroll(), Database, utc_now(), mark_device_enrolled()

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (31): WebUser, _backup_context(), backups_key_escrow_download(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), device_detail_page(), enrollment_rotate() (+23 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (16): backup_filename(), backup_keys_status(), backup_status(), _chmod_private(), list_backup_files(), _pg_dump_env(), _prune_old(), run_daily_backup() (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (20): enroll_cleartext_blocked(), request_is_cleartext(), apply_request_path(), apply_status_path(), cert_info_from_leaf(), cert_path(), _iso_z(), key_path() (+12 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (22): admin_agent_config_defaults(), admin_agent_update_set_latest(), admin_agent_update_status(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_device_config(), admin_enrollment_rotate() (+14 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (22): encrypt_secret(), set_csrf_cookie(), _clear_session_cookie(), device_archive(), device_delete(), device_restore(), _ldap_form_context(), ldap_settings_page() (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.18
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (13): compute_effective_config(), compute_setting_sources(), condition_matches(), config_local_from_meta(), config_version(), device_match_context(), _parse_bool(), policy_matches() (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (12): load_ldap_view(), try_ldap_login(), authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn() (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (12): sanitize_update_target(), ingest_uploaded_msi(), version_from_msi_name(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi() (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (16): device_silence_status(), parse_utc(), build_attention_queue(), build_bootstrap_checklist(), build_config_winner(), device_has_agent_local(), filter_devices_by_wave(), _match() (+8 more)

### Community 16 - "Community 16"
Cohesion: 0.28
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 17 - "Community 17"
Cohesion: 0.09
Nodes (20): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.16
Nodes (14): admin_token_valid(), authenticate_web_user(), get_data_key(), get_db(), get_session_secret(), require_admin_token(), require_api_key(), require_enrollment_token() (+6 more)

### Community 20 - "Community 20"
Cohesion: 0.08
Nodes (24): CpuInfo, Cores, Logical, Name, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.11
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 23 - "Community 23"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.25
Nodes (12): _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin(), get_settings() (+4 more)

### Community 26 - "Community 26"
Cohesion: 0.18
Nodes (9): AgentPolicyBody, ConfigLocalPayload, DeviceConfigOverrideBody, DeviceTagsBody, EnrollRequest, EnrollResponse, HeartbeatRequest, InventoryRequest (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.15
Nodes (8): check_update(), effective_settings_for_device(), effective_update_target_for_device(), is_newer(), ops_update_signals(), resolve_target_msi(), set_latest_msi_version(), agent_update_msi()

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (8): decrypt_secret(), _fernet_from_key(), generate_session_secret(), cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), validate_csrf()

### Community 29 - "Community 29"
Cohesion: 0.16
Nodes (6): parse_semver(), _semver_equal(), CompatConnection, connect_postgres(), _split_sql_statements(), sort_key()

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (12): DiskInfo, MediaType, Model, SizeBytes, NetworkInfo, Nics, NicInfo, Dhcp (+4 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 32 - "Community 32"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (13): ConfigLocalPayload, Keys, ServerUrl, Settings, HeartbeatQueuePayload, AgentUptimeSeconds, ConfigLocal, ConfigVersion (+5 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (4): delete_msi_version(), prune_old_msi_versions(), versions_pinned_in_config(), admin_agent_update_delete()

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 39 - "Community 39"
Cohesion: 0.21
Nodes (9): _apply_bool_form_fields(), device_config_override_save(), _filter_policy_settings(), _parse_policy_form(), _policies_context(), policy_create(), policy_update(), _settings_raw_from_form() (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (7): health_snippet(), _device_config_context(), _device_inventory_nav(), device_revoke(), device_tags_save(), _format_bytes(), _format_os()

### Community 43 - "Community 43"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.44
Nodes (9): apply_nginx(), detect_mode(), ensure_tls_dirs(), pair_ok(), promote_staging(), read_domain(), bad-apply-tls.sh script, update_cookie_secure() (+1 more)

### Community 46 - "Community 46"
Cohesion: 0.22
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 47 - "Community 47"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 48 - "Community 48"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 50 - "Community 50"
Cohesion: 0.25
Nodes (3): admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 51 - "Community 51"
Cohesion: 0.29
Nodes (3): current_web_user(), dump_session(), load_session()

### Community 52 - "Community 52"
Cohesion: 0.32
Nodes (5): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), generate_data_key()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 58 - "Community 58"
Cohesion: 0.47
Nodes (4): DEBIAN_FRONTEND, prompt(), install.sh script, step()

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (3): https_panel_url(), read_domain_from_env(), _tls_context()

## Knowledge Gaps
- **185 isolated node(s):** `AuthException`, `AuthFailed`, `Deferred`, `Error`, `Failures` (+180 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 395 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 11` to `Community 24`, `Community 1`, `Community 2`, `Community 21`?**
  _High betweenness centrality (0.283) - this node is a cross-community bridge._
- **Are the 112 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 112 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AuthException`, `AuthFailed`, `Deferred` to the rest of the system?**
  _185 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.0851063829787234 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 4` to `Community 0`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 13`, `Community 14`, `Community 15`, `Community 18`, `Community 19`, `Community 25`, `Community 27`, `Community 29`, `Community 35`, `Community 39`, `Community 42`, `Community 50`, `Community 52`, `Community 60`, `Community 63`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `Settings` (e.g. with `delete_msi_version()` and `ingest_uploaded_msi()`) actually correct?**
  _`Settings` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07781649245063879 - nodes in this community are weakly interconnected._