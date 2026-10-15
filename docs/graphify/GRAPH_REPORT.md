# Graph Report - bAD  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 644 nodes · 1571 edges · 28 communities (21 shown, 7 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 205 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `65f44f2aacad11fda89f72fd1b1ea084439825af`
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
- Community 27

## God Nodes (most connected - your core abstractions)
1. `Database` - 89 edges
2. `WebUser` - 32 edges
3. `AgentConfig` - 30 edges
4. `InventorySnapshot` - 27 edges
5. `Settings` - 20 edges
6. `BadAgent` - 18 edges
7. `BadApiClient` - 17 edges
8. `InventoryCollector` - 17 edges
9. `compute_effective_config()` - 15 edges
10. `sanitize_settings()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `sync_from_github()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `admin_token_valid()` --uses--> `Settings`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/config.py
- `current_web_user()` --uses--> `Settings`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/config.py
- `get_session_secret()` --uses--> `Settings`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/config.py
- `require_admin_token()` --uses--> `Settings`  [INFERRED]
  server/bad_server/auth.py → server/bad_server/config.py

## Import Cycles
- None detected.

## Communities (28 total, 7 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (59): sanitize_conditions(), admin_token_valid(), authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), load_ldap_view() (+51 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (33): check_update(), admin_agent_config_defaults(), admin_agent_update_status(), admin_agent_update_sync(), admin_create_policy(), admin_delete_device_override(), admin_delete_policy(), admin_device_config() (+25 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (31): is_newer(), parse_semver(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+23 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (9): sync_from_github(), _agent_update_sync_loop(), create_app(), lifespan(), get_settings(), SlidingWindowRateLimiter, hash_secret(), client() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (4): DeviceIdentity, ServiceCli, BadAgent, BadAgent.Tests

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (6): BadCli, IInventoryCollector, ReportPathResolver, CliReportTests, FakeCollector, UpdateAndServiceTests

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (8): AsciiReportWriter, HtmlReportWriter, OsInfo, Arch, Build, Caption, InstallDate, Version

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (13): compute_effective_config(), condition_matches(), config_version(), device_match_context(), _parse_bool(), policy_matches(), sanitize_settings(), test_agent_config_and_heartbeat_piggyback() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (17): AgentConfig, ApiKey, CollectHardware, CollectSoftware, CollectUsers, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (18): BadAgent, net8.0, BadAgent.Tests, coverlet.collector (6.0.0), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.NET.Test.Sdk (17.8.0), Microsoft.Win32.Registry (5.0.0) (+10 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (17): CpuInfo, Cores, Logical, Name, DiskInfo, MediaType, Model, SizeBytes (+9 more)

### Community 12 - "Community 12"
Cohesion: 0.19
Nodes (6): CollectorOptions, CollectHardware, CollectSoftware, CollectUsers, CollectorTests, FakeCollector

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (6): UpdateCheckResponse, MsiName, Sha256, UpdateAvailable, Url, Version

### Community 14 - "Community 14"
Cohesion: 0.18
Nodes (6): InstalledProgram, Name, Publisher, Version, SoftwareInfo, Programs

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (14): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Network (+6 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (11): RemoteAgentConfigResponse, Settings, Version, RemoteAgentSettings, CollectHardware, CollectSoftware, CollectUsers, HeartbeatIntervalMinutes (+3 more)

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (8): CollectorError, Error, Section, HostInfo, Domain, Hostname, Os, WmiHelper

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (8): NetworkInfo, Nics, NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 22 - "Community 22"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 23 - "Community 23"
Cohesion: 0.40
Nodes (4): built_from_commit, mode, note, tool

## Knowledge Gaps
- **94 isolated node(s):** `Cores`, `Logical`, `Name`, `MediaType`, `Model` (+89 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 202 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 20` to `Community 8`, `Community 10`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.357) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `Database` (e.g. with `check_update()` and `sync_from_github()`) actually correct?**
  _`Database` has 48 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Cores`, `Logical`, `Name` to the rest of the system?**
  _94 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.050637730820483534 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06713688610240334 - nodes in this community are weakly interconnected._