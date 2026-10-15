# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 688 nodes · 1710 edges · 29 communities (25 shown, 4 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 224 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `da8cc37e`
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
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 28

## God Nodes (most connected - your core abstractions)
1. `Database` - 97 edges
2. `WebUser` - 34 edges
3. `AgentConfig` - 30 edges
4. `InventorySnapshot` - 27 edges
5. `Settings` - 25 edges
6. `BadAgent` - 19 edges
7. `InventoryCollector` - 17 edges
8. `BadApiClient` - 17 edges
9. `compute_effective_config()` - 17 edges
10. `diff_inventory_snapshots()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `sync_from_github()` --uses--> `Database`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/db.py
- `_agent_update_sync_loop()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py
- `lifespan()` --uses--> `Database`  [INFERRED]
  server/bad_server/app.py → server/bad_server/db.py
- `admin_token_valid()` --uses--> `Database`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/db.py
- `authenticate_web_user()` --uses--> `Database`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/db.py

## Import Cycles
- None detected.

## Communities (29 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (35): check_update(), admin_agent_config_defaults(), admin_agent_update_status(), admin_agent_update_sync(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy(), admin_device_config() (+27 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (52): compute_effective_config(), condition_matches(), device_match_context(), _parse_bool(), policy_matches(), sanitize_conditions(), sanitize_settings(), authenticate_web_user() (+44 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (20): sync_from_github(), _agent_update_sync_loop(), create_app(), lifespan(), admin_token_valid(), ensure_bootstrap_secrets(), require_admin_token(), require_api_key() (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (7): BadCli, IInventoryCollector, ReportPathResolver, VersionUtil, CliReportTests, FakeCollector, UpdateAndServiceTests

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (5): DeviceIdentity, ServiceCli, WmiHelper, BadAgent, BadAgent.Tests

### Community 5 - "Community 5"
Cohesion: 0.10
Nodes (18): config_version(), is_newer(), parse_semver(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi() (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (20): device_silence_status(), health_snippet(), normalize_tags(), parse_utc(), _as_dict(), _as_list(), diff_inventory_snapshots(), _disk_key() (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (17): client(), updates_dir(), enroll_device(), test_web_policies_and_device_override(), test_enroll_inventory_get_flow(), test_health(), test_schema_version_2_with_software_accepted(), test_unknown_schema_rejected() (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (17): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.19
Nodes (3): AgentUpdater, BadApiClient, Worker

### Community 10 - "Community 10"
Cohesion: 0.10
Nodes (18): BadAgent, net8.0, BadAgent.Tests, coverlet.collector (6.0.0), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.NET.Test.Sdk (17.8.0), Microsoft.Win32.Registry (5.0.0) (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.21
Nodes (3): AsciiReportWriter, HtmlReportWriter, ReportFormat

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (18): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Network (+10 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (17): CpuInfo, Cores, Logical, Name, DiskInfo, MediaType, Model, SizeBytes (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (9): load_ldap_view(), try_ldap_login(), authenticate_user(), LdapAuthResult, LdapSettingsView, _open_bound(), _server(), settings_from_row() (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.23
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (11): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, HeartbeatIntervalMinutes (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.27
Nodes (6): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, CollectorTests, FakeCollector

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (10): HostInfo, Domain, Hostname, Os, OsInfo, Arch, Build, Caption (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.22
Nodes (4): InstalledProgram, Name, Publisher, Version

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (6): UpdateCheckResponse, MsiName, Sha256, UpdateAvailable, Url, Version

### Community 22 - "Community 22"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 23 - "Community 23"
Cohesion: 0.33
Nodes (6): NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 24 - "Community 24"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 25 - "Community 25"
Cohesion: 0.40
Nodes (4): built_from_commit, mode, note, tool

## Knowledge Gaps
- **94 isolated node(s):** `coverlet.collector (6.0.0)`, `Microsoft.Extensions.Hosting (8.0.1)`, `Microsoft.Extensions.Hosting.WindowsServices (8.0.1)`, `Microsoft.NET.Test.Sdk (17.8.0)`, `Microsoft.Win32.Registry (5.0.0)` (+89 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 211 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 9` to `Community 8`, `Community 3`?**
  _High betweenness centrality (0.356) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `Database` (e.g. with `check_update()` and `sync_from_github()`) actually correct?**
  _`Database` has 52 INFERRED edges - model-reasoned connections that need verification._
- **What connects `coverlet.collector (6.0.0)`, `Microsoft.Extensions.Hosting (8.0.1)`, `Microsoft.Extensions.Hosting.WindowsServices (8.0.1)` to the rest of the system?**
  _94 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06248600223964166 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 0` to `Community 1`, `Community 2`, `Community 5`, `Community 14`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._