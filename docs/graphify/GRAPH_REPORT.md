# Graph Report - bAD-graphify  (2026-10-15)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 466 nodes · 1060 edges · 21 communities (19 shown, 2 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 132 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `93d704d0`
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
- Community 20

## God Nodes (most connected - your core abstractions)
1. `Database` - 62 edges
2. `WebUser` - 25 edges
3. `Settings` - 20 edges
4. `InventorySnapshot` - 20 edges
5. `AgentConfig` - 18 edges
6. `BadApiClient` - 16 edges
7. `lifespan()` - 14 edges
8. `sync_from_github()` - 13 edges
9. `BadAgent` - 13 edges
10. `BadAgent` - 13 edges

## Surprising Connections (you probably didn't know these)
- `sync_from_github()` --uses--> `Settings`  [INFERRED]
  server/bad_server/agent_update.py → server/bad_server/config.py
- `admin_agent_update_status()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py
- `admin_agent_update_sync()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py
- `enroll()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py
- `inventory()` --uses--> `Settings`  [INFERRED]
  server/bad_server/api.py → server/bad_server/config.py

## Import Cycles
- None detected.

## Communities (21 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (44): admin_token_valid(), authenticate_web_user(), current_web_user(), get_data_key(), get_db(), get_session_secret(), load_ldap_view(), require_admin_token() (+36 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (19): check_update(), admin_agent_update_status(), admin_agent_update_sync(), agent_update_check(), agent_update_msi(), enroll(), get_device(), health() (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (22): is_newer(), parse_semver(), _download_bytes(), fetch_latest_release_assets(), mirror_release_to_dir(), _pick_asset(), _pick_msi(), ReleaseAssets (+14 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (16): AgentConfig, ApiKey, DeviceId, EnrollmentToken, HeartbeatIntervalMinutes, InventoryIntervalHours, ServerUrl, UpdateCheckIntervalHours (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (9): sync_from_github(), _agent_update_sync_loop(), create_app(), lifespan(), ensure_bootstrap_secrets(), get_settings(), SlidingWindowRateLimiter, client() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (10): UpdateCheckResponse, MsiName, Sha256, UpdateAvailable, Url, Version, DeviceIdentity, WmiHelper (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (3): ServiceCli, VersionUtil, UpdateAndServiceTests

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (18): BadAgent, net8.0, BadAgent.Tests, coverlet.collector (6.0.0), Microsoft.Extensions.Hosting (8.0.1), Microsoft.Extensions.Hosting.WindowsServices (8.0.1), Microsoft.NET.Test.Sdk (17.8.0), Microsoft.Win32.Registry (5.0.0) (+10 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (17): CpuInfo, Cores, Logical, Name, DiskInfo, MediaType, Model, SizeBytes (+9 more)

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (4): InventoryCollector, CollectorError, Error, Section

### Community 10 - "Community 10"
Cohesion: 0.26
Nodes (6): authenticate_user(), LdapAuthResult, LdapSettingsView, _open_bound(), _server(), test_connection()

### Community 11 - "Community 11"
Cohesion: 0.40
Nodes (8): _login(), test_admin_api_token_bearer_only(), test_change_password_clears_must_change(), test_devices_require_session(), test_ldap_settings_crud_and_test_mocked(), test_ldap_settings_requires_admin_session(), test_local_login_failure(), test_local_login_success()

### Community 12 - "Community 12"
Cohesion: 0.20
Nodes (10): HostInfo, Domain, Hostname, Os, OsInfo, Arch, Build, Caption (+2 more)

### Community 13 - "Community 13"
Cohesion: 0.20
Nodes (10): InventorySnapshot, AgentVersion, CollectedAt, CollectorErrors, DeviceId, Hardware, Host, Network (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.36
Nodes (5): IInventoryCollector, NetworkInfo, Nics, CollectorTests, FakeCollector

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (7): commandName, dotnetRunMessages, environmentVariables, DOTNET_ENVIRONMENT, profiles, BadAgent, $schema

### Community 16 - "Community 16"
Cohesion: 0.33
Nodes (6): NicInfo, Dhcp, Ipv4, Ipv6, Mac, Name

### Community 17 - "Community 17"
Cohesion: 0.50
Nodes (3): DEBIAN_FRONTEND, prompt(), install.sh script

### Community 18 - "Community 18"
Cohesion: 0.67
Nodes (3): UsersInfo, LastInteractive, LoggedOn

## Knowledge Gaps
- **73 isolated node(s):** `Domain`, `Hostname`, `Os`, `Arch`, `Build` (+68 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 163 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Worker` connect `Community 3` to `Community 4`, `Community 5`, `Community 14`?**
  _High betweenness centrality (0.425) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `Database` (e.g. with `check_update()` and `sync_from_github()`) actually correct?**
  _`Database` has 32 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Domain`, `Hostname`, `Os` to the rest of the system?**
  _73 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06582278481012659 - nodes in this community are weakly interconnected._
- **Why does `Database` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `WebUser` (e.g. with `authenticate_web_user()` and `current_web_user()`) actually correct?**
  _`WebUser` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08956228956228957 - nodes in this community are weakly interconnected._