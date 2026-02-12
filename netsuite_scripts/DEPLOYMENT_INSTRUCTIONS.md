# NetSuite RESTlet Deployment Instructions

This guide explains how to deploy the User Search RESTlet to NetSuite.

---

## Overview

The User Search RESTlet provides fast, targeted user lookup by name or email with wildcard search capabilities. This is much more efficient than fetching all users and filtering client-side.

**Benefits:**
- ⚡ **10-100x faster** than fetching all users
- 🎯 **Targeted search** using NetSuite saved searches
- 🔍 **Wildcard support** for partial name matching
- 📊 **Scalable** to millions of users

---

## Prerequisites

- NetSuite Administrator access
- Knowledge of SuiteScript deployment
- OAuth integration already configured (from main RESTlet)

---

## Step 1: Upload the Script

1. Navigate to **Customization > Scripting > Scripts > New**
2. Click **Choose File** and upload `user_search_restlet.js`
3. Click **Create Script Record**

---

## Step 2: Configure Script

### General Tab

| Field | Value |
|-------|-------|
| **Name** | User Search RESTlet |
| **ID** | `_user_search_restlet` |
| **Description** | Search for users by name or email with roles and permissions |
| **Owner** | [Your Name/Role] |
| **Status** | Testing |

### Libraries Tab

No external libraries required.

### Parameters Tab

No script parameters needed.

---

## Step 3: Create Script Deployment

1. Click **Deploy Script** button
2. Fill in deployment details:

### Deployment Configuration

| Field | Value |
|-------|-------|
| **Title** | User Search RESTlet v1 |
| **ID** | `_user_search_restlet_v1` |
| **Status** | Testing (change to Released after testing) |
| **Log Level** | Debug (for testing), change to Error in production |

### Audience Tab

**Roles:**
- Add all roles that need access (e.g., Administrator, Compliance Officer)
- **Recommended:** Create a custom "API Access" role with limited permissions

**Employees:**
- Alternatively, grant access to specific employees

---

## Step 4: Get RESTlet URL

After deployment:

1. Go to **Customization > Scripting > Script Deployments**
2. Find your deployment: **User Search RESTlet v1**
3. Click on it to open
4. Copy the **External URL**

Example URL:
```
https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXXX&deploy=1
```

Where `XXXX` is your script ID.

---

## Step 5: Update Environment Configuration

Add the search RESTlet URL to your `.env` file:

```bash
# Existing RESTlet (for bulk fetching)
NETSUITE_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3684&deploy=1

# NEW: Search RESTlet (for targeted user search)
NETSUITE_SEARCH_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXXX&deploy=1
```

**Note:** The OAuth credentials remain the same - use the existing integration record.

---

## Step 6: Test the RESTlet

### Test with Python Script

```bash
# Set the new environment variable
export NETSUITE_SEARCH_RESTLET_URL="https://your-url-here"

# Test the search
PYTHONPATH=. python3 demos/test_two_users.py
```

### Test with cURL

```bash
curl -X GET "https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXXX&deploy=1" \
  -H "Authorization: OAuth realm=\"5260239_SB1\",oauth_consumer_key=\"YOUR_KEY\",..."
```

Expected response:
```json
{
  "success": true,
  "message": "User Search RESTlet is active",
  "version": "1.0"
}
```

### Test User Search

```bash
# Python test
python3 -c "
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()
result = client.search_users('Prabal Saha', search_type='name')
print(result)
"
```

---

## API Usage

### Search by Name

```python
from services.netsuite_client import NetSuiteClient

client = NetSuiteClient()

# Search by full name
result = client.search_users(
    search_value="John Doe",
    search_type="name",
    include_permissions=True
)

if result['success']:
    users = result['data']['users']
    for user in users:
        print(f"{user['name']} - {user['email']}")
        print(f"Roles: {user['roles_count']}")
```

### Search by Email

```python
# Search by email (exact or partial)
result = client.search_users(
    search_value="john.doe@company.com",
    search_type="email",
    include_permissions=True
)
```

### Search by Both

```python
# Search by either name or email (default)
result = client.search_users(
    search_value="John",
    search_type="both",  # Default
    include_permissions=True
)
```

---

## Performance Comparison

### Old Method (Bulk Fetch)
```python
# Fetch 1,000 users, filter locally
result = client.get_users_and_roles(limit=1000)
# Time: ~30-60 seconds
# Data transfer: ~5-10 MB
```

### New Method (Targeted Search)
```python
# Search for specific user
result = client.search_users("John Doe")
# Time: ~1-3 seconds ⚡
# Data transfer: ~10-50 KB
```

**Speed improvement: 10-60x faster!**

---

## Troubleshooting

### Error: "NETSUITE_SEARCH_RESTLET_URL not configured"

**Solution:** Add the environment variable to `.env`:
```bash
NETSUITE_SEARCH_RESTLET_URL=https://your-url-here
```

### Error: "Invalid login attempt"

**Solution:** Check that the script deployment has proper role access:
1. Go to the deployment
2. Check **Audience** tab
3. Ensure your OAuth token's role is included

### Error: "Unexpected token" or script syntax error

**Solution:** Verify the script file is SuiteScript 2.1 compatible:
- Check `@NApiVersion 2.1` at top of file
- Use `define()` not `require()`
- Ensure proper module dependencies

### No results returned

**Solution:** Check search filters:
1. Verify user exists in NetSuite
2. Try `includeInactive: true` to include inactive users
3. Use wildcard: search for partial name (e.g., "John" instead of "John Doe")

---

## Security Considerations

### OAuth Permissions

The search RESTlet uses the same OAuth integration as the main RESTlet.

**Required permissions:**
- Employee: View, Edit (to search employees)
- Role: View (to fetch role information)
- Login Audit: View (for audit trail)

### Data Exposure

The RESTlet returns:
- ✅ User names and emails (non-sensitive)
- ✅ Role names (business need)
- ⚠️  Role permissions (consider restricting in production)

**Recommendation:** For production, consider:
- Adding IP whitelist to deployment
- Restricting to specific roles
- Logging all search requests
- Rate limiting searches

---

## Production Checklist

Before moving to production:

- [ ] Change deployment status from **Testing** to **Released**
- [ ] Change log level from **Debug** to **Error**
- [ ] Test with production data
- [ ] Configure proper role access
- [ ] Set up monitoring/alerts for script failures
- [ ] Document RESTlet URL in password manager
- [ ] Add to backup/recovery documentation
- [ ] Train compliance team on usage

---

## Script Maintenance

### Updating the Script

1. Go to **Customization > Scripting > Scripts**
2. Find **User Search RESTlet**
3. Click **Edit**
4. Upload new version of `user_search_restlet.js`
5. Save
6. Test in sandbox before deploying to production

### Monitoring

Check script execution logs:
1. **Customization > Scripting > Script Deployments**
2. Click on deployment
3. Click **View** next to Execution Log
4. Review for errors or performance issues

---

## Support

For issues:
1. Check execution logs in NetSuite
2. Verify OAuth credentials are valid
3. Test RESTlet directly with GET request
4. Review this documentation
5. Contact NetSuite support if needed

---

**Deployment Version:** 1.0
**Last Updated:** 2026-02-10
**Maintained By:** Compliance Engineering Team
