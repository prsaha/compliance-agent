# User Compliance Comparison Table

## 📊 Overview

A formatted ASCII table that provides side-by-side comparison of user compliance metrics. Perfect for executive reports, compliance dashboards, and quick visual assessment of multiple users.

## ✨ Features

- **Side-by-side comparison** of multiple users
- **ASCII table formatting** with borders
- **Visual indicators** (✓ for compliant, ✗ for violations, ⚠ for at-risk)
- **Comprehensive metrics** including:
  - Total Roles
  - Violation count
  - Risk Score (0-100)
  - Compliance Status
  - Issue breakdown by severity
  - Remediation time estimates
  - Priority action counts

## 🚀 Usage

### Basic Usage

```python
from agents.notifier import create_notifier
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository

# Initialize repositories
user_repo = UserRepository(session)
violation_repo = ViolationRepository(session)

# Create notifier
notifier = create_notifier(
    violation_repo=violation_repo,
    user_repo=user_repo
)

# Generate comparison table
target_emails = [
    'john.smith@company.com',
    'jane.doe@company.com'
]

comparison_table = notifier.generate_user_comparison_table(
    user_emails=target_emails,
    include_border=True
)

print(comparison_table)
```

### Sample Output

```
+-------------------+------------------------+-------------------------+
| Metric            | User: Prabal Saha      | User: Robin Turner      |
+-------------------+------------------------+-------------------------+
| Total Roles       | 2                      | 3                       |
| Violations        | 36 ✗                   | 84 ✗                    |
| Risk Score        | 94/100                 | 100/100                 |
| Compliance Status | NON-COMPLIANT          | NON-COMPLIANT           |
| Critical Issues   | 9                      | 21                      |
| High Severity     | 12                     | 28                      |
| Medium Severity   | 15                     | 35                      |
| Remediation Time  | Immediate              | Immediate               |
| Priority Actions  | 9 immediate, 12 urgent | 21 immediate, 28 urgent |
+-------------------+------------------------+-------------------------+
```

### Without Borders

```python
comparison_table = notifier.generate_user_comparison_table(
    user_emails=target_emails,
    include_border=False  # Remove ASCII borders
)
```

**Output:**
```
Metric               | User: Prabal Saha      | User: Robin Turner
Total Roles          | 2                      | 3
Violations           | 36 ✗                   | 84 ✗
Risk Score           | 94/100                 | 100/100
Compliance Status    | NON-COMPLIANT          | NON-COMPLIANT
...
```

## 📋 Metrics Explained

### Total Roles
Number of NetSuite roles assigned to the user

### Violations
Total SOD violations detected with visual indicator:
- ✗ = Has violations (non-compliant)
- ✓ = No violations (compliant)
- ⚠ = At risk (medium severity issues)

### Risk Score
Calculated risk score from 0-100 based on:
- Number of violations
- Severity of violations
- Role combinations

### Compliance Status
Overall compliance determination:
- **COMPLIANT** - No violations detected
- **REVIEW NEEDED** - Only medium severity violations
- **AT-RISK** - High severity violations present
- **NON-COMPLIANT** - Critical violations present

### Critical/High/Medium Issues
Count of violations by severity level

### Remediation Time
Estimated time to remediate based on severity:
- **Immediate** - Critical violations present
- **24 hours** - High severity violations
- **1 week** - Medium severity violations
- **None needed** - No violations

### Priority Actions
Summary of immediate actions needed:
- Format: `{count} immediate, {count} urgent`
- Based on critical and high severity violations

## 🎨 Visual Indicators

| Status | Icon | Meaning |
|--------|------|---------|
| Compliant | ✓ | No violations found |
| Non-Compliant | ✗ | Violations present |
| At-Risk | ⚠ | Review needed |

## 💼 Use Cases

### 1. Executive Dashboard

```python
# Compare all executives
executives = [
    'ceo@company.com',
    'cfo@company.com',
    'coo@company.com'
]

table = notifier.generate_user_comparison_table(executives)
print("\n📊 EXECUTIVE COMPLIANCE DASHBOARD\n")
print(table)
```

### 2. Department Comparison

```python
# Compare high-risk users
high_risk_users = [
    'finance.manager@company.com',
    'ap.clerk@company.com',
    'ar.manager@company.com'
]

table = notifier.generate_user_comparison_table(high_risk_users)
```

### 3. Email Reports

```python
# Generate table for email
table = notifier.generate_user_comparison_table(
    user_emails=['user1@company.com', 'user2@company.com'],
    include_border=True
)

# Send via email (requires SendGrid configured)
email_body = f"""
Compliance Report

{table}

Action Required: Review users marked as NON-COMPLIANT
"""

# Send email...
```

### 4. Slack Notifications

```python
# Generate table for Slack (use code block)
table = notifier.generate_user_comparison_table(users)

slack_message = f"""
:warning: *Weekly Compliance Report*

```
{table}
```

Users requiring immediate attention: 2
"""
```

## 🔧 Integration with Demo

The comparison table is automatically included in `demo_end_to_end.py`:

**Location:** Step 6 - Notification System

```python
# Generate user comparison table
target_emails = ['prabal.saha@fivetran.com', 'robin.turner@fivetran.com']
comparison_table = notifier.generate_user_comparison_table(
    user_emails=target_emails,
    include_border=True
)
print(comparison_table)
```

## 📈 Scaling to Multiple Users

The table automatically adjusts column widths based on content:

```python
# Compare 3+ users
many_users = [
    'user1@company.com',
    'user2@company.com',
    'user3@company.com',
    'user4@company.com'
]

table = notifier.generate_user_comparison_table(many_users)
# Table will have 5 columns (1 metric + 4 users)
```

**Output:**
```
+--------+---------+---------+---------+---------+
| Metric | User 1  | User 2  | User 3  | User 4  |
+--------+---------+---------+---------+---------+
| ...    | ...     | ...     | ...     | ...     |
+--------+---------+---------+---------+---------+
```

## 🎯 Best Practices

### 1. Limit Users per Table
For readability, compare 2-4 users per table. For more users, generate multiple tables.

```python
# Good
users = ['user1@co.com', 'user2@co.com', 'user3@co.com']

# Better for many users
for i in range(0, len(all_users), 3):
    batch = all_users[i:i+3]
    table = notifier.generate_user_comparison_table(batch)
    print(f"\nBatch {i//3 + 1}:")
    print(table)
```

### 2. Include Context
Always add headers and explanatory text:

```python
print("="*80)
print("  MONTHLY COMPLIANCE REVIEW")
print("  Date: 2026-02-11")
print("="*80)
print()
print(table)
print()
print("Action Items:")
print("  • Review all NON-COMPLIANT users immediately")
print("  • Schedule remediation meetings for AT-RISK users")
```

### 3. Handle Missing Users
The table gracefully handles users not found in the database:

```python
users = ['exists@co.com', 'notfound@co.com', 'another@co.com']
table = notifier.generate_user_comparison_table(users)
# Only shows users that exist in database
```

### 4. Export to File

```python
# Save to text file
with open('compliance_report.txt', 'w') as f:
    f.write("COMPLIANCE COMPARISON REPORT\n")
    f.write(f"Generated: {datetime.now()}\n\n")
    f.write(table)

# Or CSV format
import csv
# Convert table data to CSV...
```

## 🛠️ Customization

### Add Custom Metrics

To add new metrics to the table, modify `generate_user_comparison_table()` in `agents/notifier.py`:

```python
# In the metrics list
metrics = [
    ('Total Roles', 'total_roles'),
    ('Violations', 'violations', True),
    # Add your custom metric here:
    ('Last Login', 'last_login_date'),
    ('Department', 'department_name'),
    ...
]
```

### Change Column Widths

Modify `_format_comparison_table()`:

```python
# Adjust padding
col_widths.append(max_width + 4)  # More padding
```

## 📊 API Reference

### `generate_user_comparison_table(user_emails, include_border=True)`

**Parameters:**
- `user_emails` (List[str]) - List of email addresses to compare
- `include_border` (bool) - Whether to include ASCII table borders (default: True)

**Returns:**
- `str` - Formatted ASCII table

**Raises:**
- Returns "No users found for comparison" if no valid users

**Example:**
```python
table = notifier.generate_user_comparison_table(
    user_emails=['user1@co.com', 'user2@co.com'],
    include_border=True
)
```

## ✅ Testing

Test the comparison table:

```python
# Test script
python3 -c "
from agents.notifier import create_notifier
from repositories import UserRepository, ViolationRepository
from models.database_config import DatabaseConfig

session = DatabaseConfig().get_session()
notifier = create_notifier(
    violation_repo=ViolationRepository(session),
    user_repo=UserRepository(session)
)

table = notifier.generate_user_comparison_table([
    'test1@company.com',
    'test2@company.com'
])

print(table)
"
```

## 🎉 Result

You now have a professional, readable compliance comparison table that can be:
- ✅ Printed to console
- ✅ Included in email reports
- ✅ Posted to Slack
- ✅ Exported to text files
- ✅ Used in dashboards
- ✅ Integrated into automated reports

---

**Status:** ✅ IMPLEMENTED AND TESTED

**Date:** 2026-02-11

**Files Modified:**
- `agents/notifier.py` - Added comparison table methods
- `demos/demo_end_to_end.py` - Integrated into demo
