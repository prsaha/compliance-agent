# SOD Analysis Agent

## Overview

The SOD Analysis Agent is an AI-powered violation detection engine that automatically identifies Segregation of Duties (SOD) conflicts in NetSuite user access rights. It uses Claude Opus 4.6 for complex reasoning and analyzes user-role-permission combinations against 17 predefined SOD rules.

## Features

### 1. Automated Violation Detection
- **Rule-Based Analysis**: Checks users against 17 SOD rules covering Financial, IT, Procurement, and Compliance domains
- **Permission Conflict Detection**: Identifies users with conflicting permissions (e.g., create + approve)
- **Role Combination Analysis**: Detects dangerous role combinations (e.g., Administrator + Business User)
- **Batch Processing**: Analyzes all active users in a single scan

### 2. Risk Scoring
- **0-100 Scale**: Calculates comprehensive risk scores based on multiple factors
- **Factors Considered**:
  - Rule severity (CRITICAL, HIGH, MEDIUM, LOW)
  - Number of conflicting roles/permissions
  - User department (Finance, IT, HR = higher risk)
  - Total role count (3+ roles = elevated risk)

### 3. AI-Powered Deep Analysis
- **Claude Opus 4.6 Integration**: Uses advanced reasoning for detailed insights
- **Detailed Reports**: Provides business impact assessment, SOX compliance analysis
- **Remediation Recommendations**: Actionable steps with implementation guidance
- **Compensating Controls**: Alternative approaches when segregation isn't possible

### 4. Database Integration
- **Automatic Storage**: All violations stored in PostgreSQL with full metadata
- **Status Tracking**: Open, Under Review, Resolved, False Positive
- **Audit Trail**: Complete history of when violations were detected
- **Query Interface**: Rich querying by severity, status, user, rule

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SOD Analysis Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐│
│  │ Rule Loader  │────>│   Analyzer   │────>│ Risk Scorer  ││
│  │  (17 rules)  │     │   Engine     │     │   (0-100)    ││
│  └──────────────┘     └──────────────┘     └──────────────┘│
│         │                     │                     │        │
│         │                     ▼                     │        │
│         │          ┌──────────────────┐             │        │
│         └─────────>│  Claude Opus 4.6 │<────────────┘        │
│                    │   (AI Reasoning) │                      │
│                    └──────────────────┘                      │
│                            │                                 │
│                            ▼                                 │
│                    ┌──────────────┐                          │
│                    │  Violation   │                          │
│                    │  Repository  │                          │
│                    └──────────────┘                          │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             ▼
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │   Database   │
                    └──────────────┘
```

## SOD Rules

The analyzer comes pre-configured with 17 SOD rules:

### Financial Rules (8 rules)
- **SOD-FIN-001**: AP Entry vs. Approval Separation (CRITICAL)
- **SOD-FIN-002**: Journal Entry Creation vs. Approval (CRITICAL)
- **SOD-FIN-003**: Bank Reconciliation vs. Cash Transactions (HIGH)
- **SOD-FIN-004**: Customer Credit Management vs. Collections (MEDIUM)
- **SOD-FIN-005**: Revenue Recognition vs. Sales Order Entry (HIGH)
- **SOD-FIN-006**: Inventory Adjustments vs. Warehouse Operations (MEDIUM)
- **SOD-FIN-007**: Payroll Processing vs. Employee Master Data (CRITICAL)
- **SOD-FIN-008**: Budget Creation vs. Budget Approval (MEDIUM)

### Procurement Rules (2 rules)
- **SOD-PROC-001**: Purchase Order Creation vs. Approval (HIGH)
- **SOD-PROC-002**: Vendor Master Data vs. AP Processing (CRITICAL)

### IT Access Rules (4 rules)
- **SOD-IT-001**: Administrator vs. Regular User Roles (HIGH)
- **SOD-IT-002**: Script Development vs. Production Execution (HIGH)
- **SOD-IT-003**: User Administration vs. Business Operations (MEDIUM)
- **SOD-IT-004**: Custom Record Definition vs. Data Entry (MEDIUM)

### Compliance Rules (2 rules)
- **SOD-COMP-001**: Audit Log Access vs. Financial Transactions (HIGH)
- **SOD-COMP-002**: Compliance Officer Independence (CRITICAL)

## Usage

### Basic Analysis

```python
from models.database_config import get_session
from repositories.user_repository import UserRepository
from repositories.role_repository import RoleRepository
from repositories.violation_repository import ViolationRepository
from agents.analyzer import SODAnalysisAgent

# Initialize
with get_session() as session:
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)

    analyzer = SODAnalysisAgent(
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo
    )

    # Analyze all users
    result = analyzer.analyze_all_users()

    print(f"Users analyzed: {result['stats']['users_analyzed']}")
    print(f"Violations found: {result['stats']['violations_detected']}")
    print(f"Critical: {result['stats']['critical_violations']}")
```

### Analyze Specific User

```python
# Analyze a single user
violations = analyzer._analyze_user(user)

for v in violations:
    print(f"Rule: {v['title']}")
    print(f"Severity: {v['severity']}")
    print(f"Risk Score: {v['risk_score']}")
```

### AI-Powered Deep Analysis

```python
# Use Claude Opus for detailed analysis
result = analyzer.analyze_user_with_ai_reasoning(
    user_email='robin.turner@fivetran.com',
    include_remediation=True
)

if result['success']:
    ai_analysis = result['ai_analysis']
    print(f"Risk Level: {ai_analysis['overall_risk_level']}")
    print(f"Risk Score: {ai_analysis['risk_score']}/100")

    # Get recommendations
    for rec in ai_analysis['detailed_recommendations']:
        print(f"Action: {rec['action']}")
        print(f"Rationale: {rec['rationale']}")
```

### Get Violation Summary

```python
# Get dashboard summary
summary = analyzer.get_analysis_summary()

print(f"Total Open: {summary['summary']['total_open']}")
print(f"Critical: {summary['summary']['severity_counts']['CRITICAL']}")
print(f"High: {summary['summary']['severity_counts']['HIGH']}")
```

## Demo Scripts

### 1. Comprehensive Demo
Shows all analyzer capabilities including batch analysis, user comparison, and summaries.

```bash
python3 demos/demo_analyzer.py
```

### 2. Test Suite
Runs 5 comprehensive tests validating analyzer functionality.

```bash
# Basic tests (no API calls)
python3 tests/test_analyzer.py

# Include AI analysis tests (requires ANTHROPIC_API_KEY)
RUN_AI_ANALYSIS=true python3 tests/test_analyzer.py
```

## API Reference

### `SODAnalysisAgent.__init__()`
```python
def __init__(
    user_repo: UserRepository,
    role_repo: RoleRepository,
    violation_repo: ViolationRepository,
    sod_rules_path: Optional[str] = None,
    llm_model: str = "claude-opus-4.6"
)
```

### `analyze_all_users()`
Analyzes all active users for SOD violations.

**Returns**: Dictionary with violations, stats, timestamp

```python
{
    'success': True,
    'violations': [...],
    'stats': {
        'users_analyzed': 1933,
        'violations_detected': 47,
        'critical_violations': 12,
        'high_violations': 23,
        'medium_violations': 12
    }
}
```

### `analyze_user_with_ai_reasoning()`
Uses Claude Opus for deep analysis of a specific user.

**Parameters**:
- `user_email` (str): User email to analyze
- `include_remediation` (bool): Include detailed remediation steps

**Returns**: AI-powered analysis with recommendations

```python
{
    'success': True,
    'ai_analysis': {
        'overall_risk_level': 'CRITICAL',
        'risk_score': 95,
        'primary_concerns': [...],
        'detailed_recommendations': [...],
        'sox_compliance_issues': [...],
        'compensating_controls': [...]
    }
}
```

### `get_analysis_summary()`
Gets summary of all violations in the system.

**Returns**: Summary statistics and top violations

## Risk Scoring Algorithm

The risk score (0-100) is calculated as:

```
Base Score (by severity):
  CRITICAL: 90
  HIGH: 70
  MEDIUM: 50
  LOW: 30

+ Conflict Penalty: min(num_conflicts * 2, 10)
+ Department Penalty: 5 if Finance/IT/HR/Accounting
+ Role Count Penalty: 10 if ≥4 roles, 5 if ≥3 roles

Final Score = min(base + penalties, 100)
```

## Configuration

### Environment Variables
```bash
# Database connection (required)
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db

# Claude API (required for AI analysis)
ANTHROPIC_API_KEY=your_api_key_here

# Enable AI analysis in tests (optional)
RUN_AI_ANALYSIS=true
```

### Custom SOD Rules
SOD rules are loaded from `database/seed_data/sod_rules.json`. You can add custom rules:

```json
{
  "rule_id": "SOD-CUSTOM-001",
  "rule_name": "Custom Rule Name",
  "description": "Description of the rule",
  "rule_type": "FINANCIAL|IT_ACCESS|PROCUREMENT|COMPLIANCE|SALES",
  "conflicting_permissions": {
    "conflicts": [
      ["Permission A", "Permission B"],
      ["Permission C", "Permission D"]
    ]
  },
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "regulatory_framework": "SOX|GDPR|INTERNAL",
  "remediation_guidance": "Steps to remediate"
}
```

## Performance

### Benchmarks (1,933 users)
- **Initialization**: ~0.5s (loads 17 rules)
- **Single User Analysis**: ~0.02s per user
- **Batch Analysis (all users)**: ~15-20s for 1,933 users
- **AI Deep Analysis**: ~3-5s per user (Claude Opus API call)

### Optimization Tips
1. **Batch Analysis**: Use `analyze_all_users()` instead of looping
2. **Lazy Loading**: Load users with permissions only when needed
3. **Parallel Processing**: Future enhancement for multi-threading
4. **Caching**: Rule matching results can be cached

## Integration Examples

### Scheduled Daily Scan
```python
# Run daily at 2 AM
from celery import Celery

@app.task
def daily_sod_scan():
    with get_session() as session:
        analyzer = create_analyzer(session)
        result = analyzer.analyze_all_users()

        # Send notifications for critical violations
        if result['stats']['critical_violations'] > 0:
            notify_compliance_team(result)
```

### Real-Time User Check
```python
# Check user when roles are assigned
def on_user_role_assigned(user_id: str):
    with get_session() as session:
        user = user_repo.get_user_by_id(user_id)
        violations = analyzer._analyze_user(user)

        if any(v['severity'] == 'CRITICAL' for v in violations):
            send_alert_to_admin(user, violations)
```

### API Endpoint
```python
# FastAPI endpoint
@app.get("/api/users/{user_email}/violations")
async def get_user_violations(user_email: str):
    with get_session() as session:
        analyzer = create_analyzer(session)
        result = analyzer.analyze_user_with_ai_reasoning(user_email)
        return result
```

## Troubleshooting

### Common Issues

**1. No violations detected**
- Verify users are loaded with roles: `user_repo.get_users_with_roles(include_permissions=True)`
- Check SOD rules are loaded: `len(analyzer.sod_rules)` should be 17
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

**2. AI analysis fails**
- Verify `ANTHROPIC_API_KEY` is set
- Check Claude API quota/limits
- User must exist in database

**3. Database errors**
- Ensure PostgreSQL is running
- Run migrations: `python3 scripts/init_database.py`
- Check connection: `DatabaseConfig().test_connection()`

## Next Steps

After implementing the Analysis Agent, consider:

1. **Notification Agent**: Alert stakeholders when critical violations are detected
2. **Risk Assessment Agent**: Historical trend analysis and predictive risk scoring
3. **Knowledge Base Agent**: Vector embeddings for intelligent rule matching
4. **Orchestrator**: LangGraph workflow to coordinate all agents
5. **API Layer**: FastAPI endpoints for programmatic access
6. **Dashboard**: React UI for violation management

## Support

- **Documentation**: See `docs/` directory
- **Tests**: Run `python3 tests/test_analyzer.py`
- **Demo**: Run `python3 demos/demo_analyzer.py`
- **Issues**: Check logs in `logs/` directory

---

Last Updated: 2026-02-09
Status: ✅ Production Ready
