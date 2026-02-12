# NetSuite RESTlet Usage Analysis

## Overview

Your compliance agent uses **two different RESTlets** for different purposes:

| RESTlet | Purpose | When to Use |
|---------|---------|-------------|
| **sod_users_roles_restlet_optimized.js** | Bulk data sync | Fetch all/many users for full SOD analysis |
| **user_search_restlet_v5_hybrid.js** | Targeted search | Find specific users by name/email |

---

## 🎯 RESTlet #1: Bulk SOD Data Collection

**File:** `netsuite_scripts/sod_users_roles_restlet_optimized.js`
**Version:** 2.0.0-optimized
**Script Type:** Restlet (GET & POST)

### Purpose
Fetch **all users** (or filtered subsets) with their roles and permissions for comprehensive SOD compliance analysis.

### Key Features
✅ **Optimized for bulk operations** (500x faster than v1.0)
✅ **SuiteQL batch queries** for roles and permissions
✅ **Governance monitoring** with safety margins
✅ **Pagination support** (limit/offset)
✅ **Filtering** by subsidiary, department, status
✅ **Governance dashboard** in response

### API Interface

**Endpoint Methods:** GET or POST

**Request Parameters:**
```json
{
  "status": "ACTIVE",           // "ACTIVE" or "INACTIVE"
  "subsidiary": "US",           // Optional: filter by subsidiary
  "department": "Finance",      // Optional: filter by department
  "limit": 50,                  // Default: 50, Max: 200
  "offset": 0,                  // Pagination offset
  "includePermissions": true,   // Include role permissions
  "includeInactive": false      // Include inactive users
}
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "rturner",
        "internal_id": "12345",
        "name": "Robin Turner",
        "email": "robin.turner@fivetran.com",
        "status": "ACTIVE",
        "subsidiary": "Fivetran Inc",
        "department": "Finance",
        "roles": [
          {
            "role_id": "3",
            "role_name": "Administrator",
            "is_custom": false,
            "permissions": [
              {
                "permission": "TRAN_JOURNALAPPRV",
                "permission_name": "Journal Approval",
                "level": "Full"
              }
            ],
            "permission_count": 287
          }
        ],
        "roles_count": 3
      }
    ],
    "metadata": {
      "total_users": 500,
      "returned_count": 50,
      "limit": 50,
      "offset": 0,
      "next_offset": 50,
      "has_more": true,
      "execution_time_seconds": 2.3,
      "version": "2.0.0-optimized"
    },
    "governance": {
      "starting_units": 5000,
      "ending_units": 4650,
      "units_used": 350,
      "units_per_user": "7.00",
      "optimization_ratio": "500x better than v1.0",
      "warnings": [],
      "safety_margin": 100,
      "max_limit": 200
    }
  }
}
```

### Python Usage

```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()

# Fetch 50 active users
result = client.get_users_and_roles(
    status='ACTIVE',
    limit=50,
    offset=0,
    include_permissions=True
)

# Fetch all users with pagination
result = client.get_all_users_paginated(
    include_permissions=True,
    status='ACTIVE',
    page_size=50
)

# Filter by department
result = client.get_users_and_roles(
    department='Finance',
    limit=50
)
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Governance per user** | ~7 units (with permissions) |
| **Governance per user** | ~3 units (without permissions) |
| **Max users per call** | 200 (enforced) |
| **Recommended page size** | 50 users |
| **Max requests per hour** | ~14 (at 5000 units/request) |

### When to Use

✅ **Initial full sync** - Fetch all users for database population
✅ **Scheduled syncs** - Daily/weekly refresh of user data
✅ **Department audits** - Analyze all users in Finance, Accounting, etc.
✅ **Subsidiary reviews** - Check compliance for specific entities
✅ **Historical analysis** - Include inactive users to see past access

### When NOT to Use

❌ **Looking up 1-2 specific users** - Use search RESTlet instead
❌ **Real-time user queries** - Search RESTlet is faster
❌ **Interactive dashboards** - Bulk sync is too slow for UI

---

## 🔍 RESTlet #2: User Search

**File:** `netsuite_scripts/user_search_restlet_v5_hybrid.js`
**Version:** 5.0.0-hybrid
**Script Type:** Restlet (GET & POST)

### Purpose
**Quickly find specific users** by name or email for targeted SOD analysis or troubleshooting.

### Key Features
✅ **Fast targeted search** (sub-second response)
✅ **Wildcard matching** on name and email
✅ **Proven saved search** method for roles
✅ **SuiteQL for permissions** (batch fetch)
✅ **Includes inactive users** (optional)
✅ **Low governance cost** (~10-20 units per search)

### API Interface

**Endpoint Methods:** GET (info) or POST (search)

**Request Parameters:**
```json
{
  "searchType": "both",              // "name", "email", or "both"
  "searchValue": "robin.turner",     // Name or email to search
  "includePermissions": true,        // Include role permissions
  "includeInactive": false           // Include inactive users
}
```

**Response Structure:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "rturner",
        "email": "robin.turner@fivetran.com",
        "first_name": "Robin",
        "last_name": "Turner",
        "name": "Robin Turner",
        "title": null,
        "department": null,
        "subsidiary": "Fivetran Inc",
        "is_active": false,
        "internal_id": "12345",
        "roles": [
          {
            "role_id": "3",
            "role_name": "Administrator",
            "permissions": [
              {
                "key": "TRAN_JOURNALAPPRV",
                "permission": "TRAN_JOURNALAPPRV",
                "permission_name": "Journal Approval",
                "level": "Full"
              }
            ],
            "permission_count": 287
          }
        ],
        "roles_count": 3
      }
    ],
    "metadata": {
      "search_value": "robin.turner",
      "search_type": "both",
      "users_found": 1,
      "execution_time_seconds": 0.8,
      "timestamp": "2026-02-11T10:30:00Z",
      "version": "5.0.0-hybrid"
    }
  },
  "governance": {
    "starting_units": 5000,
    "ending_units": 4985,
    "units_used": 15,
    "units_per_user": "15.00"
  }
}
```

### Python Usage

```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()

# Search by email (fastest)
result = client.search_users(
    search_value='robin.turner@fivetran.com',
    search_type='email',
    include_permissions=True
)

# Search by name
result = client.search_users(
    search_value='Robin Turner',
    search_type='name',
    include_permissions=True
)

# Search by partial match (either name or email)
result = client.search_users(
    search_value='robin',
    search_type='both',
    include_permissions=True
)

# Include inactive users
result = client.search_users(
    search_value='prabal.saha@fivetran.com',
    search_type='email',
    include_permissions=True,
    include_inactive=True
)
```

### Performance Characteristics

| Metric | Value |
|--------|-------|
| **Governance per search** | ~15 units (with permissions) |
| **Governance per search** | ~5 units (without permissions) |
| **Response time** | < 1 second |
| **Max searches per hour** | ~333 (at 15 units/search) |
| **Results** | All matching users (typically 0-10) |

### When to Use

✅ **SOD violation investigation** - "Who is Robin Turner?"
✅ **User access review** - Check specific employee's permissions
✅ **Helpdesk queries** - "What roles does john.doe@company.com have?"
✅ **Real-time lookups** - Fast response for interactive tools
✅ **Testing/debugging** - Verify specific users during development

### When NOT to Use

❌ **Full user audits** - Use bulk RESTlet instead
❌ **Scheduled syncs** - Bulk RESTlet is more efficient
❌ **Large datasets** - Search is optimized for 1-10 users, not 1000

---

## 🔄 How They Work Together

### Typical Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPLIANCE AGENT WORKFLOW                 │
└─────────────────────────────────────────────────────────────┘

1. INITIAL SYNC (Daily/Weekly)
   ↓
   Use: sod_users_roles_restlet_optimized.js
   ↓
   Fetch all users in batches of 50
   ↓
   Store in local database (users, roles, permissions)
   ↓
   Run full SOD analysis on all 18 rules

2. VIOLATION DETECTED
   ↓
   "Robin Turner has Administrator + Controller roles"
   ↓
   Use: user_search_restlet_v5_hybrid.js
   ↓
   Search for "robin.turner@fivetran.com"
   ↓
   Get real-time role and permission details
   ↓
   Generate detailed violation report

3. REAL-TIME QUERIES
   ↓
   User asks: "What access does John Doe have?"
   ↓
   Use: user_search_restlet_v5_hybrid.js
   ↓
   Search for "john.doe@company.com"
   ↓
   Return role and permission summary
```

### Code Example: Hybrid Approach

```python
from services.netsuite_client import NetSuiteClient
from services.sod_analyzer import SODAnalyzer

client = NetSuiteClient()
analyzer = SODAnalyzer()

# Step 1: Bulk sync (runs daily via cron job)
def daily_sync():
    """Fetch all users and update database"""
    all_users = []
    offset = 0
    page_size = 50

    while True:
        result = client.get_users_and_roles(
            limit=page_size,
            offset=offset,
            include_permissions=True
        )

        if not result['success']:
            break

        users = result['data']['users']
        all_users.extend(users)

        # Save to database
        save_to_database(users)

        if not result['data']['metadata']['has_more']:
            break

        offset += page_size

    # Run full SOD analysis
    violations = analyzer.analyze_all_users(all_users)
    save_violations(violations)


# Step 2: Real-time user lookup
def check_user_access(email: str):
    """Quick lookup for specific user"""
    result = client.search_users(
        search_value=email,
        search_type='email',
        include_permissions=True
    )

    if result['success'] and result['data']['users']:
        user = result['data']['users'][0]
        violations = analyzer.analyze_single_user(user)
        return {
            'user': user,
            'violations': violations
        }

    return None


# Usage
# Daily sync at 2 AM
daily_sync()

# Real-time lookup
user_report = check_user_access('robin.turner@fivetran.com')
print(f"Found {len(user_report['violations'])} violations")
```

---

## 📊 Performance Comparison

| Feature | Bulk RESTlet | Search RESTlet |
|---------|--------------|----------------|
| **Primary use case** | Sync all users | Find specific users |
| **Response time** | 2-5 seconds | < 1 second |
| **Governance cost** | ~7 units/user | ~15 units/search |
| **Max results** | 200 users | All matches (0-10) |
| **Pagination** | ✅ Required | ❌ Not needed |
| **Wildcard search** | ❌ No | ✅ Yes |
| **Filter by dept** | ✅ Yes | ❌ No |
| **Filter by subsidiary** | ✅ Yes | ❌ No |
| **Search by name** | ❌ No | ✅ Yes |
| **Search by email** | ❌ No | ✅ Yes |
| **Governance dashboard** | ✅ Yes | ✅ Yes |
| **Includes inactive** | ✅ Optional | ✅ Optional |

---

## 🎛️ Configuration

### Environment Variables

```bash
# Main bulk sync RESTlet
NETSUITE_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3684&deploy=1

# User search RESTlet
NETSUITE_SEARCH_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3685&deploy=1

# OAuth credentials (shared by both)
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_REALM=5260239_SB1
```

---

## 🚀 Deployment Status

### Current Deployments

| RESTlet | Script ID | Deploy ID | Status | Version |
|---------|-----------|-----------|--------|---------|
| **Bulk Sync** | customscript_3684 | customdeploy_1 | ✅ Deployed | 2.0.0-optimized |
| **User Search** | customscript_3685 | customdeploy_1 | ⏳ **Deploy v5** | 5.0.0-hybrid (ready) |

### Next Steps

**IMPORTANT:** You need to deploy **user_search_restlet_v5_hybrid.js** to replace the current version.

**Why?** The current search RESTlet is returning 0 roles. v5 fixes this by using the proven saved search method.

**Deploy v5:**
1. NetSuite → Customization → Scripting → Scripts
2. Find: Script ID `customscript_3685`
3. Edit → Upload `user_search_restlet_v5_hybrid.js`
4. Save → Verify deployment

**Then test:**
```bash
python3 tests/test_permission_fix.py
```

---

## 💡 Best Practices

### 1. Use the Right Tool for the Job

```python
# ✅ GOOD: Use bulk sync for full analysis
result = client.get_users_and_roles(limit=50)

# ❌ BAD: Don't use search to fetch all users
for user_id in all_user_ids:  # This is VERY slow
    result = client.search_users(user_id)
```

### 2. Respect Governance Limits

```python
# ✅ GOOD: Use pagination
offset = 0
while True:
    result = client.get_users_and_roles(limit=50, offset=offset)
    # Process batch
    offset += 50

# ❌ BAD: Don't fetch 1000 users at once
result = client.get_users_and_roles(limit=1000)  # Might hit governance limit
```

### 3. Cache Bulk Data

```python
# ✅ GOOD: Sync once daily, cache in database
def daily_sync():
    users = client.get_all_users_paginated(page_size=50)
    save_to_database(users)

def get_user(email):
    return query_database(email)  # Fast local lookup

# ❌ BAD: Don't fetch from NetSuite every time
def get_user(email):
    return client.search_users(email)  # Slow, wasteful
```

### 4. Monitor Governance Usage

```python
# ✅ GOOD: Check governance in response
result = client.get_users_and_roles(limit=50)
governance = result['data']['governance']

if governance['ending_units'] < 100:
    logger.warning("Low governance remaining!")
    # Stop or reduce batch size
```

---

## 🔧 Troubleshooting

### Issue: "0 roles returned"

**Symptom:** Search RESTlet returns users but `roles_count: 0`

**Cause:** Old version (v2-v4) using incorrect method

**Fix:** Deploy v5 hybrid version

```bash
# Test after deploying v5
python3 tests/test_permission_fix.py
```

### Issue: "Governance limit exceeded"

**Symptom:** Script fails with "SSS_USAGE_LIMIT_EXCEEDED"

**Cause:** Trying to fetch too many users at once

**Fix:** Reduce page size

```python
# Change from 200 to 50
result = client.get_users_and_roles(limit=50)
```

### Issue: "Search RESTlet not configured"

**Symptom:** `search_users()` falls back to slow method

**Cause:** Missing `NETSUITE_SEARCH_RESTLET_URL` environment variable

**Fix:** Add to `.env`

```bash
NETSUITE_SEARCH_RESTLET_URL=https://...script=3685&deploy=1
```

---

## 📈 Optimization Tips

### 1. Tune Pagination Size

```python
# Start conservative
page_size = 50  # Safe default

# Monitor governance
result = client.get_users_and_roles(limit=page_size)
units_per_user = result['data']['governance']['units_per_user']

# Adjust based on results
if float(units_per_user) < 5:
    page_size = 100  # Can handle more
```

### 2. Skip Permissions When Not Needed

```python
# Faster sync without permissions (3 units vs 7 units)
result = client.get_users_and_roles(
    limit=50,
    include_permissions=False  # 2x faster
)
```

### 3. Filter at the Source

```python
# ✅ GOOD: Filter in NetSuite
result = client.get_users_and_roles(
    department='Finance',
    limit=50
)

# ❌ BAD: Filter after fetching
result = client.get_users_and_roles(limit=1000)
finance_users = [u for u in result['data']['users'] if u['department'] == 'Finance']
```

---

## 🎯 Summary

### Use **sod_users_roles_restlet_optimized.js** when:
- Running scheduled syncs (daily/weekly)
- Fetching all users for full SOD analysis
- Need to filter by department/subsidiary
- Populating database with user data

### Use **user_search_restlet_v5_hybrid.js** when:
- Looking up specific users by name/email
- Investigating SOD violations
- Real-time access queries
- Testing/debugging with specific users

### Both RESTlets:
- ✅ Use same OAuth credentials
- ✅ Return same data structure for users
- ✅ Include governance metrics
- ✅ Support permission fetching
- ✅ Support inactive users (optional)

---

## 📝 Action Items

1. ✅ **Bulk sync RESTlet** - Already optimized and deployed
2. ⏳ **Search RESTlet** - Deploy v5 hybrid version
3. ⏳ **Test v5** - Run `python3 tests/test_permission_fix.py`
4. ⏳ **Verify** - Confirm roles and permissions are returned
5. ⏳ **Update .env** - Add `NETSUITE_SEARCH_RESTLET_URL` if missing

**Priority:** Deploy v5 search RESTlet ASAP to fix the "0 roles" issue.
