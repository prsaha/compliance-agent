# NetSuite SOD Compliance & Risk Assessment Framework
## Multi-Agent Architecture Design

---

## 🎯 Objective
Automated Segregation of Duties (SOD) analysis for NetSuite users to identify, assess, and notify compliance violations in real-time.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Orchestrator Agent (Central Controller)         │
│                  - Workflow coordination & scheduling                │
│                  - State management & error handling                 │
└───────┬─────────────────────────────────────────────────────┬───────┘
        │                                                     │
        ▼                                                     ▼
┌───────────────────┐                              ┌──────────────────┐
│  Data Collection  │◄────────────────────────────►│  Knowledge Base  │
│      Agent        │                              │     Agent        │
│                   │                              │                  │
│ • Fetch Users     │                              │ • SOD Rule Store │
│ • Fetch Roles     │                              │ • Risk Policies  │
│ • Fetch Perms     │                              │ • Compliance DB  │
└─────────┬─────────┘                              └─────────┬────────┘
          │                                                  │
          ▼                                                  ▼
┌─────────────────────┐         ┌──────────────────────────────────────┐
│   Analysis Agent    │◄────────│       Risk Assessment Agent          │
│                     │         │                                      │
│ • SOD Conflict Det. │         │ • Severity Scoring (Critical/High/   │
│ • Permission Matrix │         │   Medium/Low)                        │
│ • User-Role Mapping │         │ • Business Impact Analysis           │
└─────────┬───────────┘         │ • Historical Pattern Detection       │
          │                     └──────────────┬───────────────────────┘
          │                                    │
          └────────────────┬───────────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │  Notification Agent │
                 │                     │
                 │ • Email Alerts      │
                 │ • Slack Integration │
                 │ • Dashboard Updates │
                 │ • Audit Log Export  │
                 └─────────────────────┘
```

---

## 🤖 Agent Specifications

### 1. **Data Collection Agent**
**Purpose**: Fetch real-time data from NetSuite
- **Inputs**: NetSuite credentials, API endpoints
- **Operations**:
  - Query user list with status (active/inactive)
  - Retrieve role assignments per user
  - Extract permission sets for each role
  - Fetch subsidiary/department context
- **Output**: Structured user-role-permission dataset
- **Technology**: RESTlet/SuiteTalk API integration

### 2. **Knowledge Base Agent**
**Purpose**: Maintain SOD rules and compliance standards
- **SOD Rule Categories**:
  - Financial Controls (AP/AR separation)
  - IT Access Controls (Admin vs. User roles)
  - Procurement Controls (PO creator vs. approver)
  - Custom business rules
- **Data Store**:
  - JSON/SQL database of SOD matrices
  - Regulatory frameworks (SOX, GDPR, internal policies)
- **Dynamic Updates**: Support rule versioning and audits

### 3. **Analysis Agent**
**Purpose**: Detect SOD conflicts using rules engine
- **Conflict Detection Logic**:
  ```
  FOR each user:
    assigned_roles = get_user_roles(user)
    combined_permissions = aggregate_permissions(assigned_roles)

    FOR each SOD_rule:
      IF combined_permissions contains conflicting_pair:
        flag_violation(user, rule, severity)
  ```
- **Advanced Features**:
  - Transitive permission analysis (role inheritance)
  - Temporal analysis (time-based access)
  - Custom script permission checks
- **Output**: Violation report with user, roles, conflicting permissions

### 4. **Risk Assessment Agent**
**Purpose**: Quantify and prioritize risks
- **Scoring Model**:
  - **Critical (90-100)**: Direct financial fraud risk (e.g., can create & approve vendor payments)
  - **High (70-89)**: Significant audit exposure (e.g., journal entry + approval)
  - **Medium (40-69)**: Elevated risk with mitigating controls
  - **Low (0-39)**: Minor segregation concerns
- **Risk Factors**:
  - Number of conflicting permissions
  - User's transaction history volume
  - Role sensitivity level
  - Presence of compensating controls
- **ML Enhancement** (Future): Anomaly detection based on user behavior patterns

### 5. **Notification Agent**
**Purpose**: Alert stakeholders and log violations
- **Multi-Channel Delivery**:
  - Real-time email to compliance team
  - Slack channel for critical violations
  - Dashboard widget for management
  - Weekly summary reports
- **Escalation Logic**:
  - Critical → Immediate notification + ticket creation
  - High → Daily digest
  - Medium/Low → Weekly reports
- **Audit Trail**: All violations logged to immutable compliance database

### 6. **Orchestrator Agent**
**Purpose**: Coordinate agent workflows
- **Scheduling**:
  - Continuous monitoring (every 4 hours)
  - Triggered scans (on role change events)
  - Ad-hoc compliance audits
- **Error Handling**:
  - Retry logic for API failures
  - Fallback to cached data
  - Alert on orchestration failures
- **State Management**: Track scan progress, resume from failures

---

## 🔄 Workflow Sequence

```
1. [Orchestrator] Initiates scan cycle
2. [Data Collection] Fetches users → roles → permissions from NetSuite
3. [Knowledge Base] Provides current SOD rules and policies
4. [Analysis] Processes data against SOD rules → Generates violation list
5. [Risk Assessment] Scores each violation → Prioritizes by severity
6. [Notification] Sends alerts based on severity thresholds
7. [Orchestrator] Logs results → Schedules next scan
```

**Parallel Execution**: Steps 2-3 run concurrently; Steps 4-5 pipeline results.

---

## 📊 Data Models

### User-Role-Permission Model
```json
{
  "user_id": "12345",
  "name": "John Doe",
  "email": "jdoe@company.com",
  "roles": [
    {
      "role_id": "AP_CLERK",
      "role_name": "Accounts Payable Clerk",
      "permissions": ["Create Bill", "Enter Vendor Payment"]
    }
  ],
  "subsidiaries": ["US", "EMEA"]
}
```

### Violation Record
```json
{
  "violation_id": "V-2026-001",
  "user_id": "12345",
  "detected_at": "2026-02-09T10:30:00Z",
  "conflicting_roles": ["AP_CLERK", "AP_APPROVER"],
  "sod_rule": "SOD-FIN-001: AP Entry vs. Approval",
  "risk_score": 95,
  "severity": "CRITICAL",
  "remediation": "Remove AP_APPROVER role or implement dual control"
}
```

---

## 🛠️ Technology Stack

| Component | Technology | Version/Details |
|-----------|------------|-----------------|
| **Agent Framework** | LangChain | langchain-core, langgraph for agent orchestration |
| **LLM** | Claude (Anthropic) | Claude Sonnet 4.5 (fast analysis), Opus 4.6 (complex reasoning) |
| **Vector Database** | PostgreSQL + pgvector | v16+ with pgvector extension for embeddings |
| **Embeddings** | Voyage AI / Claude Embeddings | For semantic search of SOD rules & violations |
| **NetSuite Integration** | RESTlet + SuiteTalk | OAuth 2.0 authentication |
| **Task Queue** | Celery + Redis | Background job processing |
| **Caching** | Redis | API response caching, rate limiting |
| **Notifications** | SendGrid + Slack SDK | Multi-channel alerting |
| **API Framework** | FastAPI | REST API for dashboard integration |
| **Monitoring** | Prometheus + Grafana | Agent performance metrics |

---

## 🔧 LangChain + Claude + Postgres Implementation

### LangChain Agent Architecture

```python
from langchain.agents import AgentExecutor
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Each agent implemented as LangChain ReAct agent with tools
orchestrator = create_react_agent(
    llm=ChatAnthropic(model="claude-sonnet-4-5-20250929"),
    tools=[schedule_scan, trigger_agent, handle_error],
    state_modifier="You are the orchestrator coordinating SOD compliance scans..."
)
```

**Agent Communication**:
- LangGraph for multi-agent workflows with state management
- Shared memory using Postgres-backed conversation history
- Tool calling for inter-agent communication

### Claude LLM Usage Pattern

| Agent | Claude Model | Rationale |
|-------|--------------|-----------|
| Data Collection | Sonnet 4.5 | Fast API response parsing, structured extraction |
| Knowledge Base | Sonnet 4.5 | Quick rule retrieval, embedding generation |
| Analysis | Opus 4.6 | Complex reasoning for edge cases, transitive permissions |
| Risk Assessment | Opus 4.6 | Nuanced severity scoring, business context understanding |
| Notification | Sonnet 4.5 | Template generation, message formatting |
| Orchestrator | Sonnet 4.5 | Workflow coordination, error handling |

**Claude-Specific Features**:
- **Extended Context**: 200K tokens for analyzing large user/role datasets
- **Tool Use**: Native function calling for NetSuite API integration
- **Structured Output**: JSON mode for consistent data extraction
- **Prompt Caching**: Cache SOD rules and user data for cost optimization

### Postgres + pgvector Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    status VARCHAR(20),
    last_synced_at TIMESTAMP,
    metadata JSONB
);

-- Roles table
CREATE TABLE roles (
    role_id VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(255),
    permissions TEXT[],
    sensitivity_level VARCHAR(20),
    description TEXT,
    embedding vector(1536)  -- For semantic search
);

-- User-Role assignments
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    role_id VARCHAR(50) REFERENCES roles(role_id),
    assigned_at TIMESTAMP,
    assigned_by VARCHAR(255)
);

-- SOD Rules with vector embeddings
CREATE TABLE sod_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(255),
    description TEXT,
    conflicting_permissions JSONB,  -- ["perm1", "perm2"]
    severity VARCHAR(20),
    regulatory_framework VARCHAR(50),
    embedding vector(1536),  -- Semantic search for similar rules
    created_at TIMESTAMP
);

-- Violations log
CREATE TABLE violations (
    violation_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id),
    detected_at TIMESTAMP,
    conflicting_roles VARCHAR(100)[],
    sod_rule_id VARCHAR(50) REFERENCES sod_rules(rule_id),
    risk_score INTEGER,
    severity VARCHAR(20),
    status VARCHAR(20),  -- OPEN, REMEDIATED, FALSE_POSITIVE
    remediation_plan TEXT,
    resolved_at TIMESTAMP,
    embedding vector(1536)  -- For finding similar past violations
);

-- Agent execution logs
CREATE TABLE agent_logs (
    log_id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50),
    execution_id UUID,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT
);

-- Vector similarity indexes
CREATE INDEX ON roles USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON sod_rules USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON violations USING ivfflat (embedding vector_cosine_ops);
```

### Vector Search Use Cases

**1. Semantic SOD Rule Matching**
```python
# Find similar SOD rules for new permission combinations
query = "Can create and approve purchase orders"
query_embedding = embeddings.embed_query(query)

similar_rules = db.execute("""
    SELECT rule_id, rule_name, description,
           1 - (embedding <=> %s::vector) as similarity
    FROM sod_rules
    ORDER BY embedding <=> %s::vector
    LIMIT 5
""", (query_embedding, query_embedding))
```

**2. Historical Violation Pattern Detection**
```python
# Find similar past violations for context
violation_desc = f"User {user_id} has roles {roles} with overlapping permissions"
violation_embedding = embeddings.embed_query(violation_desc)

similar_violations = db.execute("""
    SELECT violation_id, user_id, remediation_plan,
           1 - (embedding <=> %s::vector) as similarity
    FROM violations
    WHERE status = 'REMEDIATED'
    ORDER BY embedding <=> %s::vector
    LIMIT 3
""", (violation_embedding, violation_embedding))
```

**3. Natural Language Compliance Queries**
```python
# "Show me all users who can both create and approve journal entries"
nl_query = user_input
query_embedding = embeddings.embed_query(nl_query)

# Semantic search across rules and permissions
relevant_rules = vector_search(query_embedding, collection="sod_rules")
matching_violations = analyze_users_against_rules(relevant_rules)
```

### LangChain Tool Definitions

```python
from langchain.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field

class NetSuiteUserFetch(BaseModel):
    """Input for fetching NetSuite users"""
    subsidiary: str = Field(description="Subsidiary filter (optional)")
    status: str = Field(default="ACTIVE", description="User status filter")

@tool("fetch_netsuite_users", args_schema=NetSuiteUserFetch)
def fetch_netsuite_users(subsidiary: str = None, status: str = "ACTIVE"):
    """Fetch user list from NetSuite with role assignments"""
    # RESTlet API call
    users = netsuite_client.get_users(subsidiary=subsidiary, status=status)
    return users

@tool("detect_sod_violations")
def detect_sod_violations(user_data: dict):
    """Analyze user permissions against SOD rules using vector search"""
    violations = []
    for user in user_data:
        combined_perms = get_combined_permissions(user['roles'])

        # Semantic search for applicable SOD rules
        relevant_rules = vector_search_rules(combined_perms)

        for rule in relevant_rules:
            if has_conflict(combined_perms, rule['conflicting_permissions']):
                violations.append(create_violation(user, rule))

    return violations

@tool("assess_risk_score")
def assess_risk_score(violation: dict):
    """Calculate risk score using Claude LLM with historical context"""
    # Fetch similar past violations
    similar_cases = vector_search_violations(violation)

    prompt = f"""
    Assess the risk severity for this violation:
    {violation}

    Similar past cases and their outcomes:
    {similar_cases}

    Return risk score (0-100) and severity (CRITICAL/HIGH/MEDIUM/LOW)
    """

    result = claude_opus.invoke(prompt)
    return result
```

### Agent Implementation Example

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class ComplianceState(TypedDict):
    scan_id: str
    users_data: list
    sod_rules: list
    violations: list
    notifications_sent: bool
    error: str | None

def create_compliance_workflow():
    workflow = StateGraph(ComplianceState)

    # Add nodes (agents)
    workflow.add_node("collect_data", data_collection_agent)
    workflow.add_node("fetch_rules", knowledge_base_agent)
    workflow.add_node("analyze", analysis_agent)
    workflow.add_node("assess_risk", risk_assessment_agent)
    workflow.add_node("notify", notification_agent)

    # Define edges (workflow)
    workflow.set_entry_point("collect_data")
    workflow.add_edge("collect_data", "fetch_rules")
    workflow.add_edge("fetch_rules", "analyze")
    workflow.add_edge("analyze", "assess_risk")
    workflow.add_edge("assess_risk", "notify")
    workflow.add_edge("notify", END)

    return workflow.compile()

# Execute workflow
app = create_compliance_workflow()
result = app.invoke({
    "scan_id": "SCAN-2026-001",
    "users_data": [],
    "violations": [],
    "notifications_sent": False
})
```

---

## 📦 Dependencies & Requirements

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"

# LangChain ecosystem
langchain = "^0.3.0"
langchain-core = "^0.3.0"
langchain-anthropic = "^0.3.0"
langgraph = "^0.2.0"

# Claude API
anthropic = "^0.39.0"

# Database
psycopg2-binary = "^2.9.9"
pgvector = "^0.3.0"
sqlalchemy = "^2.0.25"

# Embeddings
voyageai = "^0.3.0"  # or use anthropic embeddings

# Task queue & caching
celery = "^5.3.4"
redis = "^5.0.1"

# API & Web
fastapi = "^0.115.0"
uvicorn = "^0.30.0"
pydantic = "^2.9.0"

# NetSuite integration
requests = "^2.31.0"
oauthlib = "^3.2.2"

# Notifications
sendgrid = "^6.11.0"
slack-sdk = "^3.27.0"

# Monitoring
prometheus-client = "^0.20.0"

# Development
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
black = "^24.0.0"
ruff = "^0.6.0"
```

### Environment Variables

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL_FAST=claude-sonnet-4-5-20250929
CLAUDE_MODEL_REASONING=claude-opus-4-6

# Postgres + pgvector
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db
PGVECTOR_DIMENSION=1536

# NetSuite
NETSUITE_ACCOUNT_ID=...
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://...

# Redis
REDIS_URL=redis://localhost:6379/0

# Notifications
SENDGRID_API_KEY=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Embeddings
VOYAGE_API_KEY=...  # if using Voyage AI
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Infrastructure Setup**
- Install Postgres 16+ with pgvector extension
- Set up LangChain + Claude API integration
- Configure Redis for caching and task queue
- Create database schema with vector indexes
- Set up NetSuite OAuth 2.0 authentication

**Deliverables**:
- `database/schema.sql` - Complete DB schema
- `config/claude_config.py` - LLM configuration
- `netsuite/auth.py` - NetSuite API client
- Basic Docker Compose setup

### Phase 2: Core Agents (Weeks 3-4)
**Data Collection & Knowledge Base**
- Build Data Collection Agent with LangChain tools
  - NetSuite user fetching tool
  - Role extraction tool
  - Permission aggregation tool
- Implement Knowledge Base Agent
  - SOD rule ingestion pipeline
  - Generate embeddings for rules (Voyage AI)
  - Vector search for rule retrieval
- Create initial SOD rule dataset (20+ rules)

**Deliverables**:
- `agents/data_collector.py`
- `agents/knowledge_base.py`
- `tools/netsuite_tools.py`
- `data/sod_rules.json`

### Phase 3: Analysis & Risk Assessment (Weeks 5-6)
**Intelligence Layer**
- Implement Analysis Agent with Claude Opus
  - Conflict detection algorithm
  - Transitive permission analysis
  - Vector similarity matching for edge cases
- Build Risk Assessment Agent
  - Scoring model using historical data
  - Similar violation retrieval (pgvector)
  - Business impact analysis with Claude

**Deliverables**:
- `agents/analyzer.py`
- `agents/risk_assessor.py`
- `models/scoring_model.py`
- Unit tests with mock data

### Phase 4: Orchestration & Notifications (Week 7)
**Workflow Integration**
- Build Orchestrator using LangGraph
  - State management
  - Error handling and retries
  - Parallel agent execution
- Implement Notification Agent
  - Email templates (SendGrid)
  - Slack webhooks
  - Violation dashboard feed

**Deliverables**:
- `orchestrator/workflow.py`
- `agents/notifier.py`
- `templates/email_templates/`
- Celery task definitions

### Phase 5: Testing & Optimization (Week 8)
**Quality Assurance**
- End-to-end testing with production-like data
- Performance optimization
  - Prompt caching for SOD rules
  - Batch processing for large user sets
  - Vector index tuning
- Security audit
  - Credential encryption
  - API rate limiting
  - Audit log verification

**Deliverables**:
- `tests/integration/` - Full test suite
- Performance benchmarks report
- Security audit documentation

### Phase 6: Deployment & Monitoring (Week 9+)
**Production Launch**
- Deploy to production environment
- Set up monitoring (Prometheus + Grafana)
- Configure alerting for agent failures
- Create runbook for operations team
- User training and documentation

**Deliverables**:
- Deployment scripts (Kubernetes/Docker)
- Monitoring dashboards
- Operations runbook
- User documentation

---

## 🔒 Security & Compliance

- **Credential Management**: Store NetSuite credentials in secure vault (AWS Secrets Manager)
- **Data Encryption**: Encrypt sensitive data at rest and in transit
- **Access Controls**: Role-based access to compliance dashboard
- **Audit Trail**: Immutable logs of all scans and detected violations
- **Privacy**: Anonymize user data in non-production environments

---

## 📈 Success Metrics

- **Coverage**: % of users scanned per cycle
- **Accuracy**: False positive rate < 5%
- **Performance**: Complete scan of 1000+ users in < 10 minutes
- **Response Time**: Critical violations alerted within 1 hour
- **Remediation Rate**: % of violations resolved within SLA

---

## 🔮 Future Enhancements

1. **Predictive Analytics**: ML model to predict high-risk role assignments
2. **Remediation Automation**: Suggest role optimizations to reduce violations
3. **Cross-System Analysis**: Extend to Salesforce, Workday, etc.
4. **Natural Language Queries**: "Show me all users who can both create and approve purchase orders"
5. **Blockchain Audit Trail**: Tamper-proof compliance logging

---

**Document Version**: 2.0 (Updated with LangChain + Claude + Postgres stack)
**Last Updated**: 2026-02-09
**Tech Stack**: LangChain | Claude (Anthropic) | PostgreSQL + pgvector
**Owner**: Compliance Engineering Team
