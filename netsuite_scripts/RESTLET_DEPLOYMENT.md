# NetSuite RESTlet Deployment Guide

This guide covers deploying the SOD Compliance RESTlet to your NetSuite account.

## 📋 Overview

**RESTlet**: `sod_users_roles_restlet.js`
**Purpose**: Fetch active users with their assigned roles and permissions for SOD analysis
**API Version**: SuiteScript 2.1
**Type**: RESTlet

## 🚀 Deployment Steps

### Step 1: Upload the Script File

1. **Navigate to** `Customization > Scripting > Scripts > New`
2. **Click** "Upload File" (+ icon)
3. **Create folder** (optional): `SuiteScripts/SOD_Compliance/`
4. **Upload** `sod_users_roles_restlet.js`
5. **Click** "Create Script Record"

### Step 2: Configure Script Record

1. **Script Details**:
   - **Name**: `SOD Users & Roles RESTlet`
   - **ID**: `customscript_sod_users_roles`
   - **Description**: `Fetches active users with roles and permissions for SOD compliance analysis`

2. **Script Deployments** (in same form):
   - Click **"Create Script Deployment"**
   - **Title**: `SOD Users Roles - Production`
   - **ID**: `customdeploy_sod_users_roles_prod`
   - **Status**: `Released`
   - **Log Level**: `Debug` (for initial testing, change to `Error` in production)
   - **Execute as Role**: `Administrator` (or role with full user access)
   - **Audience**: Internal only (unless needed externally)

3. **Click "Save"**

### Step 3: Get RESTlet URL

After deployment, NetSuite generates the RESTlet URL:

1. Go to script deployment record
2. Copy the **External URL** (for external OAuth) or **URL** (for internal use)

**URL Format**:
```
https://[ACCOUNT_ID].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=[SCRIPT_ID]&deploy=[DEPLOY_ID]
```

**Example**:
```
https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1
```

## 🔐 Authentication Setup

### Option 1: OAuth 2.0 (Recommended for Production)

#### 1. Create Integration Record
1. Navigate to `Setup > Integration > Manage Integrations > New`
2. Fill in:
   - **Name**: `SOD Compliance Agent`
   - **State**: `Enabled`
   - **Token-Based Authentication**: Checked
   - **OAuth 2.0**: Checked (if available)
   - **Scope**: RESTlets
3. **Save** and note:
   - Consumer Key
   - Consumer Secret

#### 2. Create Access Token
1. Navigate to `Setup > Users/Roles > Access Tokens > New`
2. Fill in:
   - **Application Name**: Select your integration
   - **User**: Your user account
   - **Role**: Administrator (or appropriate role)
   - **Token Name**: `SOD Compliance Token`
3. **Save** and note:
   - Token ID
   - Token Secret

#### 3. Add to .env
```bash
NETSUITE_ACCOUNT_ID=1234567
NETSUITE_CONSUMER_KEY=your_consumer_key_here
NETSUITE_CONSUMER_SECRET=your_consumer_secret_here
NETSUITE_TOKEN_ID=your_token_id_here
NETSUITE_TOKEN_SECRET=your_token_secret_here
NETSUITE_RESTLET_URL=https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1
```

### Option 2: NLAuth (For Testing Only)

**Not recommended for production** - credentials in clear text

```bash
NETSUITE_EMAIL=your_email@company.com
NETSUITE_PASSWORD=your_password
NETSUITE_ROLE_ID=3  # Administrator role
NETSUITE_ACCOUNT_ID=1234567
```

## 📡 API Usage

### GET Request (Simple)

Fetch all active users with default settings:

```bash
curl -X GET "https://[ACCOUNT].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1" \
  -H "Authorization: OAuth ..." \
  -H "Content-Type: application/json"
```

### POST Request (With Filters)

Fetch users with specific filters:

```bash
curl -X POST "https://[ACCOUNT].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1" \
  -H "Authorization: OAuth ..." \
  -H "Content-Type: application/json" \
  -d '{
    "status": "ACTIVE",
    "subsidiary": "US",
    "department": "Finance",
    "limit": 100,
    "offset": 0,
    "includePermissions": true
  }'
```

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | String | "ACTIVE" | User status filter (ACTIVE/INACTIVE) |
| `subsidiary` | String | null | Filter by subsidiary name |
| `department` | String | null | Filter by department name |
| `limit` | Number | 1000 | Maximum records to return |
| `offset` | Number | 0 | Starting record position |
| `includePermissions` | Boolean | true | Include detailed permissions per role |
| `includeInactive` | Boolean | false | Include inactive users |

### Response Format

```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "jdoe",
        "internal_id": "12345",
        "name": "John Doe",
        "email": "jdoe@company.com",
        "employee_id": "EMP-001",
        "status": "ACTIVE",
        "subsidiary": "United States",
        "department": "Finance",
        "last_login": "2026-02-09T10:30:00Z",
        "roles": [
          {
            "role_id": "3",
            "role_name": "Administrator",
            "is_custom": false,
            "permissions": [
              {
                "permission": "TRAN_BILL",
                "level": "FULL"
              },
              {
                "permission": "TRAN_VENDBILL",
                "level": "FULL"
              }
            ],
            "permission_count": 150
          }
        ],
        "roles_count": 1,
        "synced_at": "2026-02-09T15:45:23Z"
      }
    ],
    "metadata": {
      "total_users": 250,
      "returned_count": 100,
      "limit": 100,
      "offset": 0,
      "has_more": true,
      "filters_applied": {
        "status": "ACTIVE",
        "subsidiary": "US"
      },
      "execution_time_seconds": 3.45,
      "timestamp": "2026-02-09T15:45:23Z"
    }
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "INSUFFICIENT_PERMISSION",
  "message": "Error fetching users and roles"
}
```

## 🧪 Testing the RESTlet

### 1. Test in NetSuite

Use the **"Test"** button in the script deployment record:

**Test GET**:
- No parameters needed (uses defaults)

**Test POST**:
```json
{
  "limit": 5,
  "includePermissions": true
}
```

### 2. Test with Postman

1. **Import OAuth 1.0a settings** (NetSuite uses OAuth 1.0a, not 2.0)
2. **Configure**:
   - Consumer Key
   - Consumer Secret
   - Access Token
   - Token Secret
3. **Send request**

### 3. Test with Python

```python
from requests_oauthlib import OAuth1Session

# OAuth credentials
consumer_key = 'your_consumer_key'
consumer_secret = 'your_consumer_secret'
token = 'your_token_id'
token_secret = 'your_token_secret'

# Create OAuth session
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=token,
    resource_owner_secret=token_secret,
    realm='1234567'  # Your account ID
)

# Make request
url = 'https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1'
response = oauth.post(url, json={
    'limit': 10,
    'includePermissions': True
})

print(response.json())
```

## ⚡ Performance Considerations

### Optimization Tips

1. **Pagination**: Use `limit` and `offset` for large datasets
   ```json
   {
     "limit": 100,
     "offset": 0
   }
   ```

2. **Disable Permissions** (for faster queries):
   ```json
   {
     "includePermissions": false
   }
   ```

3. **Filter by Subsidiary/Department**:
   ```json
   {
     "subsidiary": "US",
     "department": "Finance"
   }
   ```

4. **Monitor Governance**:
   - Script execution time: ~3-5 seconds for 100 users with permissions
   - Script usage: ~500-1000 units per request
   - Stay within governance limits

### Expected Performance

| Users | Include Permissions | Time | Units |
|-------|---------------------|------|-------|
| 100 | Yes | ~3-5s | ~800 |
| 100 | No | ~1-2s | ~300 |
| 500 | Yes | ~15-20s | ~3000 |
| 500 | No | ~5-8s | ~1200 |

## 🔍 Troubleshooting

### Common Issues

#### 1. "Invalid Login" Error
- **Cause**: OAuth credentials incorrect
- **Fix**: Regenerate access token or check consumer key/secret

#### 2. "Insufficient Permissions" Error
- **Cause**: Execute As Role lacks permissions
- **Fix**: Change deployment "Execute As Role" to Administrator

#### 3. "Script Execution Time Exceeded"
- **Cause**: Too many users or complex permissions
- **Fix**: Use pagination (`limit` parameter)

#### 4. "SSS_MISSING_REQD_ARGUMENT"
- **Cause**: Missing required fields
- **Fix**: Check request body format

### Debugging

Enable detailed logging:
1. Set deployment **Log Level** to `Debug`
2. Check logs: `System > Management > System Information > View SuiteScript Execution Log`

### Script Logs

The RESTlet logs:
- Request start
- Number of users found
- Errors per user/role
- Execution time

## 🔒 Security Best Practices

1. **Use OAuth 2.0/TBA** - Never use password-based auth
2. **Restrict by IP** - In integration record, add allowed IP addresses
3. **Minimal Permissions** - Execute as role with minimum required permissions
4. **Internal Only** - Don't expose publicly unless necessary
5. **Rate Limiting** - Implement client-side rate limiting
6. **Audit Logs** - Review RESTlet access logs regularly

## 📝 Maintenance

### Regular Tasks

- **Monitor Performance**: Check execution times weekly
- **Review Logs**: Check for errors monthly
- **Update Permissions**: As new roles/permissions are added
- **Test After Updates**: Re-test after NetSuite releases

### Version Control

Keep this RESTlet in version control:
```bash
git add netsuite/sod_users_roles_restlet.js
git commit -m "Update RESTlet to version X.X"
```

## 🆘 Support

For issues with:
- **RESTlet Logic**: Review script logs and error messages
- **Authentication**: Check OAuth setup in NetSuite
- **Performance**: Use pagination and filters
- **NetSuite Issues**: Contact NetSuite support

---

**Next Step**: Configure Python Data Collection Agent to call this RESTlet
See: `agents/data_collector.py` (coming next)
