# SOD Compliance System - Hybrid Architecture

## Orchestrated Workflow (LangGraph)

This diagram shows the complete workflow orchestrated by LangGraph, with each stage numbered and indented to show the execution flow.

```mermaid
graph TD
    Start([▶ START: Compliance Scan Triggered]) --> Orchestrator

    Orchestrator[<b>🎯 ORCHESTRATOR</b><br/>LangGraph Workflow<br/>State Management & Coordination]

    Orchestrator --> S1[<b>━━━ STAGE 1: DATA COLLECTION ━━━</b>]
    S1 --> A1[1.1 📥 Data Collection Agent<br/>Claude Sonnet 4.5]
    A1 --> A1_1[1.1.1 Connect to NetSuite via OAuth]
    A1_1 --> A1_2[1.1.2 Fetch Active Users with Pagination]
    A1_2 --> A1_3[1.1.3 Collect Roles and Permissions]
    A1_3 --> DB1[(1.2 💾 Store in PostgreSQL<br/>Users, Roles, UserRoles)]
    DB1 --> C1{1.3 Success?}
    C1 -->|Yes ✓| S2[<b>━━━ STAGE 2: VIOLATION ANALYSIS ━━━</b>]
    C1 -->|No ✗| ERR[⚠️ Error Handler]

    S2 --> A2[2.1 🔍 Analysis Agent<br/>Claude Opus 4.6]
    A2 --> A2_1[2.1.1 Load 17 SOD Rules]
    A2_1 --> A2_2[2.1.2 Check Each User]
    A2_2 --> A2_3[2.1.3 Detect Conflicts]
    A2_3 --> KB[2.2 📚 Knowledge Base Agent<br/>Vector Embeddings & Search]
    KB --> KB1[2.2.1 Semantic Rule Matching]
    KB1 --> KB2[2.2.2 Find Similar Violations]
    KB2 --> DB2[(2.3 💾 Store Violations<br/>Risk Scores, Metadata)]
    DB2 --> C2{2.4 Success?}
    C2 -->|Yes ✓| S3[<b>━━━ STAGE 3: RISK ASSESSMENT ━━━</b>]
    C2 -->|No ✗| ERR

    S3 --> A3[3.1 ⚠️ Risk Assessment Agent<br/>Claude Opus 4.6]
    A3 --> A3_1[3.1.1 Calculate User Risk Scores]
    A3_1 --> A3_2[3.1.2 Analyze Historical Patterns]
    A3_2 --> A3_3[3.1.3 Detect Trends]
    A3_3 --> A3_4[3.1.4 Predict Future Risk]
    A3_4 --> A3_5[3.1.5 Calculate Org Risk]
    A3_5 --> DB3[(3.2 💾 Store Risk Data<br/>Scores, Trends, Predictions)]
    DB3 --> C3{3.3 Success?}
    C3 -->|Yes ✓| S4[<b>━━━ STAGE 4: NOTIFICATIONS ━━━</b>]
    C3 -->|No ✗| ERR

    S4 --> A4[4.1 📧 Notification Agent<br/>Multi-Channel Delivery]
    A4 --> A4_1[4.1.1 Email via SendGrid]
    A4 --> A4_2[4.1.2 Slack via Webhooks]
    A4 --> A4_3[4.1.3 Console Logging]
    A4_1 --> CHK{4.2 Critical<br/>Violations?}
    A4_2 --> CHK
    A4_3 --> CHK
    CHK -->|Yes| ALERT[4.3 🚨 Alert Team<br/>URGENT Priority]
    CHK -->|No| LOG[4.4 📝 Log Notification]
    ALERT --> S5[<b>━━━ STAGE 5: FINALIZATION ━━━</b>]
    LOG --> S5

    S5 --> F1[5.1 Create Audit Trail]
    F1 --> F2[5.2 Generate Summary Stats]
    F2 --> DB5[(5.3 💾 Store Scan Results<br/>Compliance Scans Table)]
    DB5 --> End([■ COMPLETE: Scan Finished])

    End --> API[📡 API Access<br/>17 REST Endpoints]
    End --> NEXT[⏰ Schedule Next<br/>Celery Beat - 4 hours]

    ERR --> RETRY{Retry<br/>Count < 3?}
    RETRY -->|Yes| WAIT[⏱️ Wait 5 min]
    WAIT --> S1
    RETRY -->|No| FAIL[❌ Manual Review Required]

    style Orchestrator fill:#4A90E2,stroke:#2E5C8A,stroke-width:4px,color:#fff
    style S1 fill:#50C878,stroke:#2E8B57,stroke-width:3px,color:#fff
    style S2 fill:#FF6B6B,stroke:#CC5555,stroke-width:3px,color:#fff
    style S3 fill:#FFB84D,stroke:#CC9233,stroke-width:3px,color:#fff
    style S4 fill:#9B59B6,stroke:#7D3C98,stroke-width:3px,color:#fff
    style S5 fill:#3498DB,stroke:#2874A6,stroke-width:3px,color:#fff

    style A1 fill:#E8F5E9,stroke:#4CAF50
    style A2 fill:#FFEBEE,stroke:#F44336
    style A3 fill:#FFF3E0,stroke:#FF9800
    style A4 fill:#F3E5F5,stroke:#9C27B0
    style KB fill:#FCE4EC,stroke:#E91E63

    style DB1 fill:#E3F2FD,stroke:#2196F3
    style DB2 fill:#E3F2FD,stroke:#2196F3
    style DB3 fill:#E3F2FD,stroke:#2196F3
    style DB5 fill:#E3F2FD,stroke:#2196F3

    style End fill:#4CAF50,stroke:#388E3C,stroke-width:4px,color:#fff
    style FAIL fill:#F44336,stroke:#D32F2F,stroke-width:3px,color:#fff
```

---

## Overview Architecture

```mermaid
graph TB
    subgraph "HUMAN INTERACTION (Optional - MCP)"
        H1[👤 Compliance Team]
        H2[Claude.ai / Claude Code]
        MCP[MCP Server<br/>NetSuite SOD Compliance]

        H1 -->|"Ask questions"| H2
        H2 <-->|"MCP Protocol"| MCP
    end

    subgraph "AUTOMATED AGENTS (Core - LangChain)"
        ORC[🎯 Orchestrator Agent<br/>LangGraph Workflow]
        DC[📥 Data Collection Agent<br/>Fetch Users & Roles]
        KB[📚 Knowledge Base Agent<br/>SOD Rules & Vector Search]
        AN[🔍 Analysis Agent<br/>Detect Violations]
        RA[⚠️ Risk Assessment Agent<br/>Score Severity]
        NOT[📧 Notification Agent<br/>Alert Stakeholders]

        ORC -->|"Stage 1"| DC
        ORC -->|"Stage 2"| KB
        DC -->|"User Data"| AN
        KB -->|"SOD Rules"| AN
        AN -->|"Stage 3"| RA
        RA -->|"Stage 4"| NOT
    end

    subgraph "DATA SOURCES"
        NS[NetSuite<br/>RESTlet API<br/>script=3684]
        PG[(Postgres + pgvector<br/>Users, Roles, Violations)]
        REDIS[(Redis<br/>Cache & Queue)]
    end

    subgraph "INTEGRATIONS"
        CLAUDE[Claude API<br/>Sonnet 4.5 / Opus 4.6]
        EMAIL[📧 SendGrid<br/>Email Alerts]
        SLACK[💬 Slack<br/>Notifications]
    end

    subgraph "BACKGROUND JOBS"
        CEL[Celery Worker<br/>Background Tasks]
        BEAT[Celery Beat<br/>Scheduler]

        BEAT -->|"Every 4 hours"| CEL
        CEL -->|"Run Scan"| ORC
    end

    %% Automated Agent Connections
    DC <-->|"OAuth 1.0a<br/>Fetch Users"| NS
    DC -->|"Store Users"| PG
    KB <-->|"Vector Search<br/>Similar Rules"| PG
    AN -->|"Store Violations"| PG
    RA <-->|"Historical Patterns"| PG
    NOT -->|"Log Notifications"| PG

    %% MCP Connections
    MCP <-->|"Query Violations<br/>Ad-hoc Scans"| PG
    MCP -->|"Trigger Manual Scan"| DC

    %% Cache & Queue
    DC <-->|"Cache API<br/>Responses"| REDIS
    CEL <-->|"Task Queue"| REDIS

    %% AI & Notifications
    AN <-->|"Reasoning"| CLAUDE
    RA <-->|"Risk Scoring"| CLAUDE
    NOT -->|"Send Email"| EMAIL
    NOT -->|"Send Alert"| SLACK

    %% Styling
    classDef agent fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef mcp fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef external fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class ORC,DC,KB,AN,RA,NOT agent
    class H1,H2,MCP mcp
    class NS,PG,REDIS data
    class CLAUDE,EMAIL,SLACK external
```

## Detailed Data Flow

```mermaid
sequenceDiagram
    participant Schedule as Celery Beat<br/>(Scheduler)
    participant Worker as Celery Worker
    participant Orch as Orchestrator<br/>Agent
    participant DataCol as Data Collection<br/>Agent
    participant NS as NetSuite<br/>RESTlet
    participant DB as Postgres<br/>Database
    participant Analyze as Analysis<br/>Agent
    participant Risk as Risk Assessment<br/>Agent
    participant Notify as Notification<br/>Agent
    participant Claude as Claude API
    participant Slack as Slack

    rect rgb(240, 248, 255)
        Note over Schedule,Worker: AUTOMATED SCAN (Every 4 hours)
        Schedule->>Worker: Trigger compliance_scan task
        Worker->>Orch: Start workflow
    end

    rect rgb(255, 250, 240)
        Note over Orch,NS: PHASE 1: DATA COLLECTION
        Orch->>DataCol: Fetch users & roles
        DataCol->>NS: POST /restlet?script=3684<br/>{"limit": 1000, "includePermissions": true}
        NS-->>DataCol: {users: [...], metadata: {...}}
        DataCol->>DB: INSERT INTO users, roles, user_roles
        DataCol-->>Orch: 1,933 users fetched
    end

    rect rgb(240, 255, 240)
        Note over Orch,Claude: PHASE 2: ANALYSIS
        Orch->>Analyze: Analyze for SOD violations
        Analyze->>DB: SELECT users, roles, permissions
        Analyze->>Claude: Check permission conflicts
        Claude-->>Analyze: Detected 15 violations
        Analyze->>DB: INSERT INTO violations
        Analyze-->>Orch: 15 violations found
    end

    rect rgb(255, 245, 240)
        Note over Orch,Claude: PHASE 3: RISK ASSESSMENT
        Orch->>Risk: Score violations
        Risk->>DB: SELECT violations, historical patterns
        Risk->>Claude: Assess severity with context
        Claude-->>Risk: 3 Critical, 5 High, 7 Medium
        Risk->>DB: UPDATE violations SET risk_score
        Risk-->>Orch: Risk scoring complete
    end

    rect rgb(255, 240, 245)
        Note over Orch,Slack: PHASE 4: NOTIFICATIONS
        Orch->>Notify: Send alerts
        Notify->>DB: SELECT violations WHERE severity='CRITICAL'
        Notify->>Slack: POST webhook (3 critical violations)
        Slack-->>Notify: Message sent
        Notify->>DB: INSERT INTO notifications
        Notify-->>Orch: Notifications sent
    end

    rect rgb(245, 245, 245)
        Note over Schedule,Orch: COMPLETION
        Orch-->>Worker: Scan complete (15 violations)
        Worker-->>Schedule: Task finished
    end
```

## MCP Interactive Flow (Optional)

```mermaid
sequenceDiagram
    participant Human as 👤 Compliance<br/>Team Member
    participant Claude as Claude.ai /<br/>Claude Code
    participant MCP as MCP Server<br/>(NetSuite SOD)
    participant DB as Postgres<br/>Database
    participant NS as NetSuite<br/>RESTlet

    rect rgb(255, 252, 230)
        Note over Human,Claude: HUMAN-IN-THE-LOOP QUERY
        Human->>Claude: "Check if john.doe@fivetran.com<br/>has any SOD violations"
        Claude->>MCP: call_tool("get_user_violations",<br/>{email: "john.doe@fivetran.com"})
    end

    rect rgb(240, 248, 255)
        Note over MCP,DB: QUERY EXISTING DATA
        MCP->>DB: SELECT * FROM violations<br/>WHERE user_id = 'john.doe@fivetran.com'
        DB-->>MCP: 2 violations found
        MCP-->>Claude: [{violation: "SOD-FIN-001", ...}]
        Claude-->>Human: "John Doe has 2 violations:<br/>1. Can create AND approve bills<br/>2. Has Admin + AP Clerk roles"
    end

    rect rgb(240, 255, 240)
        Note over Human,NS: AD-HOC SCAN REQUEST
        Human->>Claude: "Run a fresh scan for the<br/>Finance department"
        Claude->>MCP: call_tool("scan_department",<br/>{department: "Finance"})
        MCP->>NS: POST /restlet<br/>{"department": "Finance", "limit": 500}
        NS-->>MCP: {users: [...]}
        MCP->>DB: Analyze & store results
        MCP-->>Claude: "Found 8 new violations<br/>in Finance department"
        Claude-->>Human: "Scan complete! Found 8 violations:<br/>- 2 Critical<br/>- 3 High<br/>- 3 Medium"
    end
```

## Agent Architecture Detail

```mermaid
graph LR
    subgraph "Data Collection Agent"
        DC1[NetSuite Client<br/>OAuth 1.0a]
        DC2[Data Parser<br/>JSON to Models]
        DC3[Database Writer<br/>Bulk Insert]

        DC1 --> DC2 --> DC3
    end

    subgraph "Knowledge Base Agent"
        KB1[SOD Rules Store<br/>Postgres]
        KB2[Vector Embeddings<br/>pgvector]
        KB3[Semantic Search<br/>Similar Rules]

        KB1 --> KB2 --> KB3
    end

    subgraph "Analysis Agent"
        AN1[User-Role Aggregator]
        AN2[Permission Combiner]
        AN3[Conflict Detector<br/>Claude Opus]
        AN4[Violation Generator]

        AN1 --> AN2 --> AN3 --> AN4
    end

    subgraph "Risk Assessment Agent"
        RA1[Historical Context<br/>Vector Search]
        RA2[Severity Scorer<br/>Claude Opus]
        RA3[Business Impact<br/>Analyzer]

        RA1 --> RA2 --> RA3
    end

    subgraph "Notification Agent"
        NO1[Severity Filter<br/>Critical/High/Medium]
        NO2[Template Generator<br/>Claude Sonnet]
        NO3[Multi-Channel Send<br/>Email + Slack]

        NO1 --> NO2 --> NO3
    end

    DC3 -.->|User Data| AN1
    KB3 -.->|SOD Rules| AN3
    AN4 -.->|Violations| RA1
    RA3 -.->|Scored Violations| NO1
```

## Technology Stack

```mermaid
graph TB
    subgraph "Frontend (Future)"
        UI[React Dashboard<br/>Violation Viewer]
        GRAF[Grafana<br/>Metrics & Monitoring]
    end

    subgraph "Backend - Agents"
        LANG[LangChain 0.3+<br/>Agent Framework]
        GRAPH[LangGraph<br/>Workflow Engine]
        ANTHRO[Anthropic SDK<br/>Claude Integration]
    end

    subgraph "Backend - API"
        FAST[FastAPI<br/>REST Endpoints]
        PYDANTIC[Pydantic 2.9<br/>Data Validation]
    end

    subgraph "Task Processing"
        CEL[Celery 5.3<br/>Background Jobs]
        BEAT[Celery Beat<br/>Scheduler]
        RED[(Redis 7<br/>Broker + Cache)]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 16<br/>Main Database)]
        PGVEC[pgvector Extension<br/>Embeddings]
        SQLA[SQLAlchemy 2.0<br/>ORM]
    end

    subgraph "External Services"
        NS[NetSuite RESTlet<br/>SuiteScript 2.1]
        CL[Claude API<br/>Sonnet 4.5 / Opus 4.6]
        SG[SendGrid<br/>Email Service]
        SL[Slack API<br/>Notifications]
    end

    subgraph "Optional: MCP"
        MCPS[MCP Server<br/>Python/uv]
        MCPC[Claude Desktop<br/>MCP Client]
    end

    UI --> FAST
    GRAF --> PG

    FAST --> LANG
    LANG --> GRAPH
    LANG --> ANTHRO

    GRAPH --> CEL
    CEL --> RED
    BEAT --> RED

    LANG --> SQLA
    SQLA --> PG
    PG --> PGVEC

    LANG --> NS
    ANTHRO --> CL
    CEL --> SG
    CEL --> SL

    MCPS --> PG
    MCPC --> MCPS

    style LANG fill:#4fc3f7
    style GRAPH fill:#4fc3f7
    style CL fill:#ff6b6b
    style NS fill:#90ee90
    style PG fill:#ba68c8
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Local Development"
        DEV[Developer Machine<br/>MacOS]
        DOCK[Docker Compose<br/>Postgres + Redis]

        DEV --> DOCK
    end

    subgraph "Production (Future)"
        K8S[Kubernetes Cluster]

        subgraph "Pods"
            API[FastAPI Pod<br/>3 replicas]
            WORK[Celery Worker Pod<br/>5 replicas]
            SCHED[Celery Beat Pod<br/>1 replica]
        end

        subgraph "Data Services"
            PGPROD[(PostgreSQL<br/>RDS/Cloud SQL)]
            REDPROD[(Redis<br/>ElastiCache)]
        end

        K8S --> API
        K8S --> WORK
        K8S --> SCHED

        API --> PGPROD
        WORK --> PGPROD
        WORK --> REDPROD
        SCHED --> REDPROD
    end

    subgraph "External"
        NSPROD[NetSuite Production<br/>RESTlet]
        CLPROD[Claude API<br/>Anthropic]
    end

    WORK --> NSPROD
    API --> CLPROD
    WORK --> CLPROD
```

---

## Summary

**Core System (LangChain):**
- ✅ Automated compliance scanning
- ✅ Multi-agent workflow with LangGraph
- ✅ Scheduled background jobs (Celery)
- ✅ Direct NetSuite integration
- ✅ Postgres storage with vector search

**Optional Enhancement (MCP):**
- 💡 Human-in-the-loop queries
- 💡 Ad-hoc compliance checks
- 💡 Interactive investigation
- 💡 Accessible via Claude.ai or Claude Code

**Best of Both Worlds:**
- Automation for routine scans
- Human interaction for investigations
- Shared data layer (Postgres)
- Claude-powered intelligence throughout
