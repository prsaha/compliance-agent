# SOD Compliance - Lucidchart Compatible Diagrams

## Diagram 1: System Overview (Simplified)

```mermaid
graph TB
    Human[Compliance Team]
    Claude[Claude AI]
    MCP[MCP Server]

    Orchestrator[Orchestrator Agent]
    DataCollector[Data Collection Agent]
    Analyzer[Analysis Agent]
    RiskAgent[Risk Assessment Agent]
    Notifier[Notification Agent]

    NetSuite[NetSuite RESTlet]
    Postgres[(Postgres Database)]
    Redis[(Redis Cache)]

    Email[Email - SendGrid]
    Slack[Slack Notifications]

    Human --> Claude
    Claude --> MCP
    MCP --> Postgres

    Orchestrator --> DataCollector
    Orchestrator --> Analyzer
    Orchestrator --> RiskAgent
    Orchestrator --> Notifier

    DataCollector --> NetSuite
    DataCollector --> Postgres
    Analyzer --> Postgres
    RiskAgent --> Postgres
    Notifier --> Email
    Notifier --> Slack
    Notifier --> Postgres

    Analyzer --> Claude
    RiskAgent --> Claude
```

## Diagram 2: Data Flow Sequence

```mermaid
sequenceDiagram
    participant Scheduler
    participant Orchestrator
    participant DataCollector
    participant NetSuite
    participant Database
    participant Analyzer
    participant RiskAgent
    participant Notifier
    participant Slack

    Scheduler->>Orchestrator: Trigger scan
    Orchestrator->>DataCollector: Fetch users
    DataCollector->>NetSuite: GET users with roles
    NetSuite-->>DataCollector: Return user data
    DataCollector->>Database: Store users
    Orchestrator->>Analyzer: Analyze violations
    Analyzer->>Database: Query users and roles
    Analyzer->>Database: Store violations
    Orchestrator->>RiskAgent: Score risks
    RiskAgent->>Database: Get violations
    RiskAgent->>Database: Update risk scores
    Orchestrator->>Notifier: Send alerts
    Notifier->>Slack: Send critical alerts
    Notifier->>Database: Log notifications
```

## Diagram 3: Agent Components

```mermaid
graph LR
    DC1[NetSuite OAuth Client]
    DC2[Data Parser]
    DC3[Database Writer]

    KB1[SOD Rules Store]
    KB2[Vector Embeddings]
    KB3[Semantic Search]

    AN1[User Role Aggregator]
    AN2[Permission Combiner]
    AN3[Conflict Detector]
    AN4[Violation Generator]

    DC1 --> DC2
    DC2 --> DC3

    KB1 --> KB2
    KB2 --> KB3

    AN1 --> AN2
    AN2 --> AN3
    AN3 --> AN4
```

## Diagram 4: Technology Stack

```mermaid
graph TB
    LangChain[LangChain Framework]
    LangGraph[LangGraph Workflows]
    FastAPI[FastAPI REST API]
    Celery[Celery Workers]
    Postgres[PostgreSQL Database]
    Redis[Redis Cache]
    Claude[Claude API]
    NetSuite[NetSuite RESTlet]

    LangChain --> LangGraph
    LangGraph --> Celery
    Celery --> Redis
    FastAPI --> LangChain
    LangChain --> Postgres
    LangChain --> Claude
    LangChain --> NetSuite
```

## Diagram 5: Simple Workflow

```mermaid
flowchart TD
    Start([Start Compliance Scan])
    Fetch[Fetch Users from NetSuite]
    Store[Store in Database]
    Analyze[Analyze SOD Violations]
    Score[Score Risk Levels]
    Notify[Send Notifications]
    End([End])

    Start --> Fetch
    Fetch --> Store
    Store --> Analyze
    Analyze --> Score
    Score --> Notify
    Notify --> End
```

## Diagram 6: MCP Interaction

```mermaid
sequenceDiagram
    participant User
    participant Claude
    participant MCP
    participant Database

    User->>Claude: Ask about violations
    Claude->>MCP: Query user violations
    MCP->>Database: SELECT violations
    Database-->>MCP: Return results
    MCP-->>Claude: Violation data
    Claude-->>User: Formatted response
```

---

## Alternative: Simple Box Diagram (Always Works)

If Mermaid still fails, here's a plain text version you can manually create:

```
┌─────────────────────────────────────────────────────────┐
│                   SOD COMPLIANCE SYSTEM                  │
└─────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│  HUMAN INTERFACE │         │  AUTOMATED AGENTS │
│                  │         │                  │
│  • Claude.ai     │         │  • Orchestrator  │
│  • MCP Server    │         │  • Data Collector│
│  • Ad-hoc Queries│         │  • Analyzer      │
│                  │         │  • Risk Assessor │
│                  │         │  • Notifier      │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         └──────────┬─────────────────┘
                    │
         ┌──────────▼─────────┐
         │   DATA LAYER       │
         │                    │
         │  • Postgres DB     │
         │  • pgvector        │
         │  • Redis Cache     │
         └──────────┬─────────┘
                    │
         ┌──────────▼─────────┐
         │  EXTERNAL SERVICES │
         │                    │
         │  • NetSuite        │
         │  • Claude API      │
         │  • SendGrid        │
         │  • Slack           │
         └────────────────────┘

DATA FLOW:
1. NetSuite → Users & Roles → Postgres
2. Postgres → Analyzer → Violations
3. Violations → Risk Scoring → Notifications
4. Humans → MCP → Postgres → Insights
```

---

## Tips for Lucidchart

If you're still having issues:

1. **Import one diagram at a time** - Don't paste all at once
2. **Use flowchart instead of graph** - Change `graph TB` to `flowchart TD`
3. **Remove special characters** - Simplify node labels
4. **Use basic syntax** - Avoid advanced features like styling

Try starting with **Diagram 5 (Simple Workflow)** - it's the most compatible!
