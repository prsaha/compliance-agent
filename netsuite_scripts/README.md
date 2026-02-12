# NetSuite RESTlets - Production Versions

This directory contains the **current production versions** of NetSuite RESTlets for SOD compliance analysis.

## 📦 Production Files

### 1. sod_users_roles_restlet_optimized.js

**Version:** 2.1.0-optimized-fixed
**Script ID:** customscript_3684
**Deploy ID:** customdeploy_1
**Status:** ✅ Production

**Purpose:** Bulk user synchronization for SOD compliance analysis

**Use Cases:**
- Daily/weekly full user sync
- Fetch all users with roles and permissions
- Department or subsidiary filtering
- Scheduled batch processing

**Performance:**
- ~450 governance units per 50 users
- ~9 units per user (with permissions)
- Response time: 3-4 seconds

**Key Features:**
- Pagination support (50-200 users per request)
- Saved search for roles (proven method)
- SuiteQL for permissions (efficient batch query)
- Governance monitoring with safety limits
- Graceful degradation on low governance

**API Example:**
```javascript
POST https://[account].restlets.api.netsuite.com/...?script=3684&deploy=1

Body:
{
  "status": "ACTIVE",
  "limit": 50,
  "offset": 0,
  "includePermissions": true,
  "includeInactive": false,
  "department": "Finance"  // Optional
}
```

**Python Usage:**
```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()
result = client.get_users_and_roles(
    limit=50,
    offset=0,
    include_permissions=True
)
```

---

### 2. user_search_restlet_v5_hybrid.js

**Version:** 5.0.0-hybrid
**Script ID:** customscript_3685
**Deploy ID:** customdeploy_1
**Status:** ✅ Production

**Purpose:** Fast targeted user search by name or email

**Use Cases:**
- Look up specific users
- SOD violation investigation
- Real-time access queries
- Testing and debugging

**Performance:**
- ~15 governance units per search
- Response time: < 1 second
- Returns 0-10 users (all matches)

**Key Features:**
- Wildcard search on name and email
- Same proven saved search method for roles
- SuiteQL for permissions (batch fetch)
- Include inactive users (optional)
- Low governance cost

**API Example:**
```javascript
POST https://[account].restlets.api.netsuite.com/...?script=3685&deploy=1

Body:
{
  "searchType": "email",
  "searchValue": "robin.turner@fivetran.com",
  "includePermissions": true,
  "includeInactive": false
}
```

**Python Usage:**
```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()
result = client.search_users(
    search_value='robin.turner@fivetran.com',
    search_type='email',
    include_permissions=True
)
```

---

## 🔄 Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| **v2.1** | 2026-02-11 | Fixed bulk RESTlet to use saved search | ✅ Current |
| **v5.0** | 2026-02-11 | Hybrid search with saved search + SuiteQL | ✅ Current |
| v2.0 | 2026-02-11 | Bulk optimization (SuiteQL - failed) | ❌ Archived |
| v2-v4 | 2026-02-11 | Search fixes (various approaches - failed) | ❌ Archived |
| v1.0 | 2026-02-09 | Original versions | ✅ Archived |

---

## 🏗️ Architecture

Both RESTlets use the same proven architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    PROVEN ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────┘

1. User Search
   └─→ search.create(type: EMPLOYEE)
       └─→ Returns: user_id, email, name, status, etc.

2. Role Fetching (PROVEN METHOD)
   └─→ search.create(type: EMPLOYEE)
       └─→ columns: ['role' with summary: GROUP]
       └─→ Returns: role_id, role_name

3. Permission Fetching (EFFICIENT)
   └─→ query.runSuiteQL('SELECT FROM RolePermissions ...')
       └─→ Batch query for all roles at once
       └─→ Returns: permissions by role
```

### Why This Works

**Saved Search for Roles:**
- ✅ Proven to work in this NetSuite environment
- ✅ Reliable access to employee-role mapping
- ✅ Returns role ID and name
- ⚠️ Slightly higher governance (~2 units per batch)

**SuiteQL for Permissions:**
- ✅ RolePermissions table is accessible
- ✅ Efficient batch queries
- ✅ Returns key, name, level for each permission
- ✅ Low governance (1 query for all roles)

### What Doesn't Work

❌ **SuiteQL EntityRole table** - Returns 0 results
❌ **SuiteQL employeeroles table** - Returns 0 results
❌ **record.load() roles sublist** - Returns 0 lines

**Lesson:** Stick with what works!

---

## 📋 Deployment Guide

### Prerequisites

1. NetSuite account with admin access
2. OAuth 1.0a credentials configured
3. Integration permissions:
   - ✅ Employee: View
   - ✅ Role: View
   - ✅ Lists: View
   - ✅ SuiteQL: Execute

### Deploy Bulk RESTlet (v2.1)

```
1. Navigate: Customization → Scripting → Scripts
2. Find: customscript_3684
3. Click: Edit
4. Upload: sod_users_roles_restlet_optimized.js
5. Save
6. Verify: Version shows "2.1.0-optimized-fixed"
7. View Deployments → Verify: Status = "Released"
```

### Deploy Search RESTlet (v5.0)

```
1. Navigate: Customization → Scripting → Scripts
2. Find: customscript_3685
3. Click: Edit
4. Upload: user_search_restlet_v5_hybrid.js
5. Save
6. Verify: Version shows "5.0.0-hybrid"
7. View Deployments → Verify: Status = "Released"
```

---

## 🧪 Testing

### Test Both RESTlets

```bash
# Test search RESTlet
python3 tests/test_permission_fix.py

# Test bulk RESTlet
python3 tests/diagnose_role_issue.py

# Full integration test
python3 demos/test_two_users.py
```

### Expected Results

**Search RESTlet (v5):**
```
✅ Robin Turner: 3 roles, 494 permissions
✅ Prabal Saha: 2 roles, 253 permissions
```

**Bulk RESTlet (v2.1):**
```
✅ 20/20 users have roles
✅ Average: 9 units per user
```

---

## 📊 Performance Metrics

### Bulk RESTlet (50 users/batch)

| Metric | Value |
|--------|-------|
| Governance per batch | ~450 units |
| Governance per user | ~9 units |
| Response time | 3-4 seconds |
| Users per request | 50-200 (configurable) |
| Max batches per hour | ~11 (at 450 units/batch) |

### Search RESTlet (per search)

| Metric | Value |
|--------|-------|
| Governance per search | ~15 units |
| Response time | < 1 second |
| Results | 0-10 users |
| Max searches per hour | ~333 |

---

## 🔒 Environment Variables

```bash
# Bulk sync RESTlet
NETSUITE_RESTLET_URL=https://[account].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3684&deploy=1

# User search RESTlet
NETSUITE_SEARCH_RESTLET_URL=https://[account].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3685&deploy=1

# OAuth credentials (shared)
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_REALM=...
```

---

## 📚 Documentation

- **RESTLET_USAGE_ANALYSIS.md** - Detailed comparison and usage guide
- **BULK_RESTLET_FIX.md** - v2.1 fix documentation
- **PERMISSION_FIX_DEPLOYMENT.md** - v5 deployment guide
- **archive/README.md** - Archived versions explanation

---

## 🚨 Troubleshooting

### Issue: "0 roles returned"

**Check:**
1. Version deployed (should be v2.1 or v5.0)
2. NetSuite execution logs for errors
3. OAuth permissions (Employee, Role, Lists)

**Fix:** Deploy latest version from this directory

### Issue: "Governance limit exceeded"

**Reduce batch size:**
```python
# Change from 200 to 50
result = client.get_users_and_roles(limit=50)
```

### Issue: "Search RESTlet not found"

**Check:**
1. NETSUITE_SEARCH_RESTLET_URL in .env
2. Script deployment status in NetSuite
3. URL has correct script ID (3685)

---

## 📞 Support

**Check NetSuite Logs:**
```
Customization → Scripting → Script Execution Log
Filter by script ID: 3684 or 3685
```

**Verify in NetSuite UI:**
```
Lists → Employees → [Find user]
→ Open record → Access tab
→ Verify roles exist
```

---

## 🎯 Quick Reference

| Task | RESTlet | Python Method |
|------|---------|---------------|
| Daily sync | Bulk (v2.1) | `get_users_and_roles()` |
| Find user | Search (v5) | `search_users()` |
| Department audit | Bulk (v2.1) | `get_users_and_roles(department='Finance')` |
| User lookup | Search (v5) | `search_users('email@company.com')` |

---

**Last Updated:** 2026-02-11
**Maintained By:** Compliance Team
**Production Status:** ✅ Both RESTlets deployed and working
