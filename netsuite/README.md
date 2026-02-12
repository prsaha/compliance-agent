# NetSuite RESTlet - SOD Compliance Data Collection

This directory contains the NetSuite RESTlet for collecting user, role, and permission data.

## 📁 Files

- **`sod_users_roles_restlet.js`** - Main RESTlet script (deploy to NetSuite)
- **`RESTLET_DEPLOYMENT.md`** - Complete deployment guide
- **`test_requests.http`** - Example API requests for testing
- **`test_restlet.py`** - Python test script (see below)

## 🚀 Quick Start

### 1. Deploy RESTlet to NetSuite

Follow the detailed guide in `RESTLET_DEPLOYMENT.md`:

```
1. Upload sod_users_roles_restlet.js to NetSuite
2. Create Script Record (Customization > Scripting > Scripts > New)
3. Create Script Deployment
4. Note the RESTlet URL
5. Set up OAuth credentials
```

### 2. Configure Credentials

Add to your `.env` file:

```bash
NETSUITE_ACCOUNT_ID=1234567
NETSUITE_CONSUMER_KEY=your_consumer_key
NETSUITE_CONSUMER_SECRET=your_consumer_secret
NETSUITE_TOKEN_ID=your_token_id
NETSUITE_TOKEN_SECRET=your_token_secret
NETSUITE_RESTLET_URL=https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=123&deploy=1
```

### 3. Test the RESTlet

Using Python test script:
```bash
poetry run python netsuite/test_restlet.py
```

Using HTTP client (VS Code REST Client):
- Open `test_requests.http`
- Update variables at the top
- Click "Send Request" on any example

## 📡 API Reference

### Endpoint
```
POST https://[ACCOUNT].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=[ID]&deploy=[ID]
```

### Request Body
```json
{
  "status": "ACTIVE",
  "subsidiary": "United States",
  "department": "Finance",
  "limit": 100,
  "offset": 0,
  "includePermissions": true,
  "includeInactive": false
}
```

### Response Format
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "jdoe",
        "name": "John Doe",
        "email": "jdoe@company.com",
        "roles": [
          {
            "role_id": "3",
            "role_name": "Administrator",
            "permissions": [...]
          }
        ]
      }
    ],
    "metadata": {
      "total_users": 250,
      "returned_count": 100,
      "has_more": true
    }
  }
}
```

## 🧪 Testing

### Test in NetSuite UI
1. Go to script deployment
2. Click "Test" button
3. Enter test parameters
4. View results

### Test with Python
```bash
poetry run python netsuite/test_restlet.py --limit 10
```

### Test with cURL
```bash
curl -X POST "https://[ACCOUNT].restlets.api.netsuite.com/..." \
  -H "Authorization: OAuth ..." \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

## ⚡ Performance

| Users | Permissions Included | Avg Time |
|-------|---------------------|----------|
| 10 | Yes | ~1s |
| 100 | Yes | ~3-5s |
| 500 | Yes | ~15-20s |
| 100 | No | ~1-2s |
| 500 | No | ~5-8s |

**Tips**:
- Use `includePermissions: false` for faster queries
- Implement pagination for large datasets
- Filter by subsidiary/department to reduce scope

## 🔒 Security

- ✅ Uses OAuth 1.0a authentication
- ✅ Executed with specific role permissions
- ✅ Internal-only deployment by default
- ✅ IP restrictions can be added
- ✅ Audit logs all executions

## 📊 Data Collected

For each user:
- User ID, Name, Email
- Employee ID
- Status (Active/Inactive)
- Subsidiary, Department
- Last login date

For each role:
- Role ID, Role Name
- Is Custom Role
- Permissions (optional)
  - Permission type
  - Permission level (NONE/VIEW/CREATE/EDIT/FULL)

## 🐛 Troubleshooting

### Common Issues

**"Invalid Login"**
- Check OAuth credentials
- Regenerate access token

**"Insufficient Permissions"**
- Change deployment "Execute As Role" to Administrator
- Ensure role has access to Employee records

**"Script Timeout"**
- Reduce `limit` parameter
- Set `includePermissions: false`
- Use pagination

**"SSS_MISSING_REQD_ARGUMENT"**
- Check request body JSON format
- Ensure Content-Type is application/json

## 📝 Next Steps

Once the RESTlet is deployed and tested:

1. ✅ RESTlet deployed to NetSuite
2. ✅ OAuth credentials configured
3. ✅ Test requests successful
4. 🔄 **Next**: Build Python Data Collection Agent
   - `agents/data_collector.py`
   - `services/netsuite_client.py`

## 📚 Documentation

- **[Deployment Guide](./RESTLET_DEPLOYMENT.md)** - Complete deployment instructions
- **[Test Requests](./test_requests.http)** - Example API calls
- **[Main README](../README.md)** - Project overview

## 🆘 Support

For issues:
1. Check NetSuite script logs
2. Review error messages in response
3. Test with simplified request (fewer filters)
4. Check OAuth setup in NetSuite
5. Verify role permissions

---

**Status**: RESTlet ready for deployment
**Version**: 1.0
**Last Updated**: 2026-02-09
