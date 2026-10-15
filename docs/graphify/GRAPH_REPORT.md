# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 992 nodes · 2703 edges · 67 communities (48 shown, 19 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 381 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1e0f5a54`
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
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
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
- Community 59
- Community 60
- Community 61
- Community 66

## God Nodes (most connected - your core abstractions)
1. `Database` - 172 edges
2. `WebUser` - 61 edges
3. `Settings` - 54 edges
4. `_html()` - 40 edges
5. `HardwareInfo` - 35 edges
6. `AgentConfig` - 35 edges
7. `InventoryCollector` - 31 edges
8. `InventorySnapshot` - 28 edges
9. `BadAgent` - 21 edges
10. `CollectorError` - 20 edges

## Surprising Connections (you probably didn't know these)
- `try_ldap_login()` --uses--> `LdapGroupDenied`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/ldap_client.py
- `load_ldap_view()` --uses--> `LdapSettingsView`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/ldap_client.py
- `authenticate_web_user()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/sessions.py
- `require_web_user()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/sessions.py
- `_backup_context()` --uses--> `WebUser`  [INFERRED]
  server/bad_server/web.py → server/bad_server/sessions.py

## Import Cycles
- None detected.

## Communities (67 total, 19 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (33): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings() (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (10): AsciiReportWriter, BadCli, HtmlReportWriter, CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, IInventoryCollector (+2 more)

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (23): admin_agent_update_set_latest(), admin_agent_update_sync(), admin_agent_update_upload(), admin_create_policy(), admin_enrollment_rotate(), admin_set_device_override(), admin_update_policy(), archive_device() (+15 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (5): admin_get_policy(), list_events(), try_local_login(), Database, utc_now()

### Community 4 - "Community 4"
Cohesion: 0.20
Nodes (5): InventoryCollector, CollectorError, Error, Section, WmiHelper

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (22): get_data_key(), get_db(), get_session_secret(), require_web_user(), _apply_bool_form_fields(), _clear_session_cookie(), devices_csv_export(), devices_page() (+14 more)

### Community 6 - "Community 6"
Cohesion: 0.16
Nodes (22): Settings, _backup_context(), backups_settings_page(), backups_settings_run(), backups_site_bundle_download(), device_archive(), _device_config_context(), device_config_override_save() (+14 more)

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (4): AgentApiException, IsAuthFailure, BadApiClient, Worker

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (20): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.13
Nodes (12): OfflineQueue, MetaPath, QueueDir, QueueItem, Attempts, Body, CreatedAtUtc, Id (+4 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (24): DiskInfo, MediaType, Model, SizeBytes, HardwareInfo, Battery, BiosManufacturer, BiosReleaseDate (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (3): versions_pinned_in_config(), get_device(), list_devices()

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (5): delete_msi_version(), prune_old_msi_versions(), set_latest_msi_version(), admin_agent_update_delete(), admin_agent_update_status()

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (9): authenticate_user(), LdapAuthResult, LdapGroupDenied, LdapSettingsView, _open_bound(), _resolve_group_dn(), _server(), test_connection() (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.23
Nodes (12): build_alert_email(), build_inventory_events_email(), _dispatch(), dump_notify_flags(), filter_events_for_mail(), notify_enroll(), notify_inventory_events(), notify_stale_device() (+4 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (14): InstalledProgram, Name, Publisher, Version, NetworkInfo, Nics, NicInfo, Dhcp (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.24
Nodes (9): admin_token_valid(), require_admin_token(), require_api_key(), require_enrollment_token(), api_key_lookup(), constant_time_equals(), extract_bearer(), generate_token() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.28
Nodes (10): sync_from_github(), _agent_update_sync_loop(), _backup_loop(), create_app(), lifespan(), _retention_prune_loop(), _stale_alert_loop(), seed_default_admin() (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (11): authenticate_web_user(), load_ldap_view(), try_ldap_login(), settings_from_row(), _ldap_form_context(), ldap_settings_page(), ldap_settings_save(), ldap_settings_test() (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (13): BadAgent, net8.0, Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.Win32.Registry (5.0.0), Serilog.Extensions.Hosting (8.0.0), Serilog.Sinks.Console (6.0.0), Serilog.Sinks.File (6.0.0) (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (15): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Minidumps (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (10): OfflineFlushResult, AuthException, AuthFailed, Deferred, Error, Failures, NextRetryUtc, RetryAfter (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (8): ensure_bootstrap_secrets(), _persist(), _read_secret_file(), _write_secret_file(), decrypt_secret(), _fernet_from_key(), generate_data_key(), generate_session_secret()

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (11): _as_dict(), _as_list(), _cpu_label(), diff_inventory_snapshots(), _disk_key(), _nic_ipv4_set(), _norm_str(), _ram_module_key() (+3 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (13): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, DesiredAgentVersion (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.24
Nodes (7): current_web_user(), require_web_admin(), dump_session(), load_session(), WebUser, password_submit(), _set_session_cookie()

### Community 28 - "Community 28"
Cohesion: 0.17
Nodes (10): UpdateCheckResponse, Action, Desired, MsiName, Reason, Sha256, TargetVersion, UpdateAvailable (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.22
Nodes (3): _add_file(), build_site_bundle(), _utc_stamp()

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (12): HostInfo, AdDistinguishedName, AdOu, Domain, Hostname, Os, OsInfo, Arch (+4 more)

### Community 33 - "Community 33"
Cohesion: 0.35
Nodes (5): backup_filename(), backup_status(), list_backup_files(), run_daily_backup(), utc_today()

### Community 34 - "Community 34"
Cohesion: 0.24
Nodes (6): cookie_secure_for_request(), ensure_csrf(), get_csrf_token(), new_csrf_token(), set_csrf_cookie(), validate_csrf()

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (7): admin_agent_config_defaults(), admin_device_config(), admin_list_policies(), agent_config(), agent_update_check(), agent_update_msi(), health()

### Community 36 - "Community 36"
Cohesion: 0.23
Nodes (9): devices, idx_snapshots_device_received, inventory_snapshots, site_secrets, agent_policies, device_config_overrides, device_events, idx_device_events_created (+1 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (11): RamModuleInfo, BankLabel, CapacityBytes, Channel, DeviceLocator, FormFactor, Manufacturer, MemoryType (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (6): enrollment_status(), enrollment_token_file(), rotate_enrollment_token(), site_env_path(), _update_site_env_enrollment(), _write_private_file()

### Community 40 - "Community 40"
Cohesion: 0.27
Nodes (9): _html(), _parse_policy_form(), render(), _policies_context(), policies_page(), policy_create(), policy_edit_page(), policy_update() (+1 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (10): MinidumpFileInfo, ModifiedAt, Name, SizeBytes, MinidumpInfo, Count, Files, MemoryDmpModifiedAt (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.31
Nodes (7): encrypt_secret(), mail_settings_page(), mail_settings_save(), mail_settings_test(), _parse_smtp_form(), _smtp_form_context(), SmtpFormData

### Community 44 - "Community 44"
Cohesion: 0.25
Nodes (8): MonitorInfo, Height, Manufacturer, Name, SerialNumber, Week, Width, Year

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (8): HeartbeatQueuePayload, AgentUptimeSeconds, ConfigVersion, DeviceId, LastInventoryAt, LastInventoryError, LastInventoryOk, SystemDriveFreeBytes

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 49 - "Community 49"
Cohesion: 0.25
Nodes (3): admin_delete_device_override(), admin_delete_policy(), delete_device()

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (5): UpdateAction, Downgrade, None, Upgrade, UpdatePlan

### Community 52 - "Community 52"
Cohesion: 0.33
Nodes (6): BatteryInfo, ChargePercent, EstimatedRuntimeMinutes, Name, Status, StatusCode

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (6): GpuInfo, AdapterRamBytes, DriverVersion, Name, PnpDeviceId, Vendor

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (3): _device_inventory_nav(), _format_bytes(), _format_os()

### Community 56 - "Community 56"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (4): CpuInfo, Cores, Logical, Name

## Knowledge Gaps
- **178 isolated node(s):** `CollectHardware`, `CollectSoftware`, `CollectUsers`, `MediaType`, `Model` (+173 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 349 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 7` to `Community 8`, `Community 17`, `Community 1`, `Community 38`?**
  _High betweenness centrality (0.268) - this node is a cross-community bridge._
- **Are the 103 inferred relationships involving `Database` (e.g. with `check_update()` and `delete_msi_version()`) actually correct?**
  _`Database` has 103 INFERRED edges - model-reasoned connections that need verification._
- **What connects `CollectHardware`, `CollectSoftware`, `CollectUsers` to the rest of the system?**
  _178 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.055135135135135134 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 3` to `Community 0`, `Community 2`, `Community 35`, `Community 5`, `Community 38`, `Community 39`, `Community 6`, `Community 40`, `Community 11`, `Community 12`, `Community 43`, `Community 49`, `Community 18`, `Community 19`, `Community 20`, `Community 24`, `Community 27`, `Community 30`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Are the 51 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08502415458937199 - nodes in this community are weakly interconnected._