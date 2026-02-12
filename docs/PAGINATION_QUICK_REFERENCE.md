# Pagination Quick Reference

**Version:** 2.0.0 | **Last Updated:** 2026-02-11

---

## 🚀 Quick Start

### Basic Pagination Loop

```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()
all_users = []
offset = 0
limit = 50  # Default: 50 users per request

while True:
    # Fetch batch
    result = client.get_users_and_roles(
        include_permissions=True,
        limit=limit,
        offset=offset
    )

    # Check success
    if not result['success']:
        print(f"Error: {result.get('error')}")
        break

    # Extract data
    users = result['data']['users']
    metadata = result['data']['metadata']
    governance = result['data'].get('governance', {})

    # Add to collection
    all_users.extend(users)

    # Log progress
    print(f"Fetched {len(users)} users (total: {len(all_users)}/{metadata['total_users']})")
    print(f"Governance: {governance['units_used']} units ({governance['units_per_user']} per user)")

    # Check for more data
    if not metadata['has_more']:
        print("✓ All users fetched")
        break

    # Continue with next batch
    offset = metadata['next_offset']

print(f"\n✅ Total: {len(all_users)} users processed")
```

---

## 📊 Response Structure

### Complete Response Example

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "john.doe@company.com",
        "internal_id": "12345",
        "name": "John Doe",
        "email": "john.doe@company.com",
        "department": "Finance",
        "roles": [
          {
            "role_id": "3",
            "role_name": "Administrator",
            "is_custom": false,
            "permissions": [
              {
                "permission": "LIST_ACCOUNT",
                "permission_name": "Accounts",
                "level": "Full"
              }
            ],
            "permission_count": 245
          }
        ],
        "roles_count": 1,
        "synced_at": "2026-02-11T10:30:00Z"
      }
    ],
    "metadata": {
      "total_users": 1247,
      "returned_count": 50,
      "limit": 50,
      "offset": 0,
      "next_offset": 50,
      "has_more": true,
      "execution_time_seconds": 2.45,
      "timestamp": "2026-02-11T10:30:00Z",
      "version": "2.0.0-optimized"
    },
    "governance": {
      "starting_units": 5000,
      "ending_units": 4965,
      "units_used": 35,
      "units_per_user": "0.70",
      "optimization_ratio": "500x better than v1.0",
      "warnings": [],
      "safety_margin": 100,
      "max_limit": 200
    }
  }
}
```

---

## ⚙️ Configuration Options

### Request Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 50 | 200 | Users per request |
| `offset` | int | 0 | ∞ | Starting position |
| `includePermissions` | bool | true | - | Fetch detailed permissions |
| `includeInactive` | bool | false | - | Include inactive users |
| `status` | string | "ACTIVE" | - | Filter by status |
| `department` | string | null | - | Filter by department |
| `subsidiary` | string | null | - | Filter by subsidiary |

### Usage Examples

```python
# Default (50 users, active only, with permissions)
result = client.get_users_and_roles()

# Small batch (10 users)
result = client.get_users_and_roles(limit=10)

# Large batch (200 users - maximum)
result = client.get_users_and_roles(limit=200)

# Without permissions (faster)
result = client.get_users_and_roles(include_permissions=False)

# Include inactive users
result = client.get_users_and_roles(include_inactive=True)

# Filter by department
result = client.get_users_and_roles(department="Finance")

# Pagination with offset
result = client.get_users_and_roles(limit=50, offset=100)
```

---

## 📋 Common Patterns

### Pattern 1: Fetch All Users

```python
def fetch_all_users(client):
    """Fetch all users with pagination"""
    all_users = []
    offset = 0

    while True:
        result = client.get_users_and_roles(limit=50, offset=offset)

        if not result['success']:
            break

        all_users.extend(result['data']['users'])

        if not result['data']['metadata']['has_more']:
            break

        offset = result['data']['metadata']['next_offset']

    return all_users
```

### Pattern 2: Fetch with Progress Bar

```python
from tqdm import tqdm

def fetch_with_progress(client):
    """Fetch all users with progress indicator"""
    # Get total count first
    result = client.get_users_and_roles(limit=1)
    total = result['data']['metadata']['total_users']

    all_users = []
    offset = 0

    with tqdm(total=total, desc="Fetching users") as pbar:
        while True:
            result = client.get_users_and_roles(limit=50, offset=offset)

            if not result['success']:
                break

            users = result['data']['users']
            all_users.extend(users)
            pbar.update(len(users))

            if not result['data']['metadata']['has_more']:
                break

            offset = result['data']['metadata']['next_offset']

    return all_users
```

### Pattern 3: Adaptive Batch Size

```python
def fetch_adaptive(client, target_units_per_user=0.5):
    """Automatically adjust batch size based on governance"""
    all_users = []
    offset = 0
    limit = 50  # Start with default

    while True:
        result = client.get_users_and_roles(limit=limit, offset=offset)

        if not result['success']:
            break

        users = result['data']['users']
        governance = result['data']['governance']

        all_users.extend(users)

        # Adjust batch size based on governance efficiency
        units_per_user = float(governance['units_per_user'])

        if units_per_user > target_units_per_user:
            # Reduce batch size
            limit = max(10, limit // 2)
            print(f"⚠️  Reducing batch size to {limit}")
        elif units_per_user < target_units_per_user * 0.5:
            # Increase batch size
            limit = min(200, limit * 2)
            print(f"✓ Increasing batch size to {limit}")

        # Check for warnings
        if governance['warnings']:
            limit = max(10, limit // 2)
            print(f"⚠️  Governance warning: reducing to {limit}")

        if not result['data']['metadata']['has_more']:
            break

        offset = result['data']['metadata']['next_offset']

    return all_users
```

### Pattern 4: Parallel Department Fetch

```python
import concurrent.futures

def fetch_by_departments(client, departments):
    """Fetch users from multiple departments in parallel"""
    all_users = []

    def fetch_department(dept):
        users = []
        offset = 0

        while True:
            result = client.get_users_and_roles(
                limit=50,
                offset=offset,
                department=dept
            )

            if not result['success']:
                break

            users.extend(result['data']['users'])

            if not result['data']['metadata']['has_more']:
                break

            offset = result['data']['metadata']['next_offset']

        return dept, users

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fetch_department, dept): dept
            for dept in departments
        }

        for future in concurrent.futures.as_completed(futures):
            dept, users = future.result()
            print(f"✓ {dept}: {len(users)} users")
            all_users.extend(users)

    return all_users

# Usage
departments = ['Finance', 'IT', 'Sales', 'Operations']
users = fetch_by_departments(client, departments)
```

### Pattern 5: Error Handling with Retry

```python
import time

def fetch_with_retry(client, max_retries=3):
    """Fetch with exponential backoff retry"""
    all_users = []
    offset = 0

    while True:
        for attempt in range(max_retries):
            try:
                result = client.get_users_and_roles(limit=50, offset=offset)

                if result['success']:
                    break

                # Wait before retry
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"⚠️  Retry in {wait}s...")
                    time.sleep(wait)

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Failed after {max_retries} attempts: {e}")
                    return all_users
                time.sleep(2 ** attempt)

        if not result['success']:
            print(f"❌ Failed: {result.get('error')}")
            break

        users = result['data']['users']
        all_users.extend(users)

        if not result['data']['metadata']['has_more']:
            break

        offset = result['data']['metadata']['next_offset']

    return all_users
```

---

## ⚠️ Common Mistakes

### ❌ DON'T: Calculate offset yourself

```python
# BAD
offset = offset + len(users)  # Might skip or duplicate records
```

### ✅ DO: Use provided next_offset

```python
# GOOD
offset = metadata['next_offset']
```

---

### ❌ DON'T: Assume more data based on count

```python
# BAD
if len(users) == limit:
    # This might be wrong - could be last batch
```

### ✅ DO: Check has_more flag

```python
# GOOD
if metadata['has_more']:
    # Continue pagination
```

---

### ❌ DON'T: Ignore governance warnings

```python
# BAD
result = client.get_users_and_roles(limit=50)
users = result['data']['users']
# No governance check
```

### ✅ DO: Monitor governance metrics

```python
# GOOD
result = client.get_users_and_roles(limit=50)
governance = result['data']['governance']

if governance['warnings']:
    print(f"⚠️  Warnings: {governance['warnings']}")

print(f"Efficiency: {governance['units_per_user']} units/user")
```

---

### ❌ DON'T: Request too many at once

```python
# BAD
result = client.get_users_and_roles(limit=1000)  # Might fail
```

### ✅ DO: Use recommended batch size

```python
# GOOD
result = client.get_users_and_roles(limit=50)  # Default, safe
```

---

## 📊 Governance Guidelines

### Target Metrics

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Units per User | < 0.7 | 0.7-1.0 | > 1.0 |
| Warnings | 0 | 1-2 | > 2 |
| Execution Time (50 users) | < 5s | 5-10s | > 10s |
| Ending Units | > 1000 | 500-1000 | < 500 |

### Monitoring Example

```python
def monitor_governance(result):
    """Check governance metrics and log warnings"""
    governance = result['data']['governance']
    metadata = result['data']['metadata']

    units_per_user = float(governance['units_per_user'])
    warnings = governance['warnings']
    exec_time = metadata['execution_time_seconds']

    # Check efficiency
    if units_per_user > 1.0:
        print(f"🔴 CRITICAL: {units_per_user} units/user (target: < 0.7)")
    elif units_per_user > 0.7:
        print(f"🟡 WARNING: {units_per_user} units/user (target: < 0.7)")
    else:
        print(f"✅ GOOD: {units_per_user} units/user")

    # Check warnings
    if len(warnings) > 2:
        print(f"🔴 CRITICAL: {len(warnings)} governance warnings")
    elif len(warnings) > 0:
        print(f"🟡 WARNING: {len(warnings)} governance warnings")
        for warning in warnings:
            print(f"   - {warning}")

    # Check execution time
    users_count = metadata['returned_count']
    if exec_time > 10:
        print(f"🔴 CRITICAL: {exec_time:.2f}s for {users_count} users")
    elif exec_time > 5:
        print(f"🟡 WARNING: {exec_time:.2f}s for {users_count} users")
```

---

## 🔗 Related Documentation

- **Full Guide:** [RESTLET_OPTIMIZATION_GUIDE.md](RESTLET_OPTIMIZATION_GUIDE.md)
- **Performance Comparison:** [compare_old_vs_new.py](../tests/compare_old_vs_new.py)
- **Test Suite:** [test_restlet_optimization.py](../tests/test_restlet_optimization.py)
- **Optimized RESTlet:** [sod_users_roles_restlet_optimized.js](../netsuite_scripts/sod_users_roles_restlet_optimized.js)

---

**Need Help?**
- Review the full [Optimization Guide](RESTLET_OPTIMIZATION_GUIDE.md)
- Run tests: `python3 tests/test_restlet_optimization.py`
- Check troubleshooting section in main guide
