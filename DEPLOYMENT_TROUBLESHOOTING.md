# Deployment Troubleshooting Guide

**Issue:** NetSuite still serving old version after deployment
**Current Version:** 2.0.0-with-permissions
**Target Version:** 2.1.1-with-permissions-fixed

---

## 🔍 Quick Diagnosis

Check which version is deployed:

```bash
python3 -c "
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()
result = client.search_users('test@test.com', 'email', False)
print('Current Version:', result['data']['metadata'].get('version'))
"
```

**Expected:** `2.1.1-with-permissions-fixed`
**Actual:** `2.0.0-with-permissions` ❌

---

## ✅ Deployment Checklist

### Step 1: Verify File Upload

1. **Open NetSuite**
2. Navigate to: **Customization → Scripting → Scripts**
3. Find script (ID: 3685)
4. Click **"View"** (not Edit)
5. Look for **"Script File"** field
6. **Check filename** - should show `user_search_restlet_with_permissions_v2.1.js`

**If wrong file:**
- Click **"Edit"**
- Click **"Script File"** field
- Click **"Replace"**
- Upload: `user_search_restlet_with_permissions_v2.1.js`
- Click **"Save"**

---

### Step 2: Check Deployment Status

1. Still in the script, click **"Deployments"** tab
2. Find deployment (ID: 1)
3. **Check Status** - must be **"Released"**
4. **Check "Deployed"** checkbox - must be ✅ **checked**

**If status is not "Released":**
- Click **"Edit"** on deployment
- Change Status to **"Released"**
- Click **"Save"**

---

### Step 3: Clear NetSuite Cache

**Option A: Clear Script Cache**
1. Navigate to: **Setup → Company → General Preferences**
2. Click **"Clear Cache"** button
3. Wait 2-3 minutes

**Option B: Force Reload**
1. Add `&_cache=false` to RESTlet URL in browser
2. Or add timestamp: `&_t=1707679200`

---

### Step 4: Verify Deployment

Wait **2-3 minutes** after clearing cache, then test:

```bash
python3 -c "
from services.netsuite_client import NetSuiteClient
import time

client = NetSuiteClient()

for i in range(3):
    print(f'Attempt {i+1}/3...')
    result = client.search_users('test@test.com', 'email', False)
    version = result['data']['metadata'].get('version')
    print(f'  Version: {version}')

    if version == '2.1.1-with-permissions-fixed':
        print('  ✅ SUCCESS - Correct version deployed!')
        break
    else:
        print('  ⚠️  Still old version, waiting 30s...')
        if i < 2:
            time.sleep(30)
"
```

---

## 🐛 Common Issues

### Issue 1: Script File Not Replaced

**Symptoms:**
- Clicked "Save" but version didn't change
- File size didn't change

**Solution:**
1. Click **"Edit"** on script
2. Click **"Script File"** → **"Replace"** (not "Remove")
3. Browse and select: `user_search_restlet_with_permissions_v2.1.js`
4. Verify file name appears in field
5. Click **"Save"** button at bottom
6. Wait for "Script saved successfully" message

---

### Issue 2: Deployment Not Released

**Symptoms:**
- File uploaded but old version still serves
- Deployment status shows "Not Deployed" or "Testing"

**Solution:**
1. Go to **"Deployments"** tab
2. Click **"Edit"** on deployment row
3. **Status** field: Select **"Released"**
4. **Deployed** checkbox: Must be ✅ **checked**
5. Click **"Save"**

---

### Issue 3: Cache Not Cleared

**Symptoms:**
- Everything looks correct but old version still serves
- Other scripts work but this one doesn't

**Solution:**
1. **Clear browser cache** (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
2. **Clear NetSuite cache:**
   - Setup → Company → General Preferences → Clear Cache
3. **Wait 5 minutes** - NetSuite caching can be aggressive
4. **Try incognito/private window** to bypass browser cache

---

### Issue 4: Wrong Script ID

**Symptoms:**
- Changes deployed but test still shows old version
- Different script is being called

**Solution:**

Check environment variable:
```bash
echo $NETSUITE_SEARCH_RESTLET_URL
```

Should show: `...?script=3685&deploy=1`

If wrong script ID, update `.env` file:
```bash
NETSUITE_SEARCH_RESTLET_URL=https://[realm].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3685&deploy=1
```

---

## 🔧 Alternative: Create New Deployment

If clearing cache doesn't work, create a fresh deployment:

### Step 1: Create New Deployment

1. In script page, click **"Deployments"** tab
2. Click **"New Deployment"**
3. Set **Title:** "User Search v2.1.1"
4. Set **ID:** "2" (or next available)
5. Set **Status:** "Released"
6. Check **"Deployed"** box
7. Set **Audience:** "All Roles"
8. Click **"Save"**

### Step 2: Update Environment Variable

Update `.env` file:
```bash
# Old (deployment 1):
NETSUITE_SEARCH_RESTLET_URL=...?script=3685&deploy=1

# New (deployment 2):
NETSUITE_SEARCH_RESTLET_URL=...?script=3685&deploy=2
```

### Step 3: Test

```bash
python3 tests/test_permission_fix.py
```

---

## 📋 Complete Deployment Process

### The Correct Way

1. ✅ **Upload Script File**
   - Script → Edit → Script File → Replace
   - Select: `user_search_restlet_with_permissions_v2.1.js`
   - Save

2. ✅ **Verify Deployment**
   - Deployments tab → Edit
   - Status: "Released"
   - Deployed: ✅ Checked
   - Save

3. ✅ **Clear Cache**
   - Setup → Company → General Preferences → Clear Cache
   - Wait 2-3 minutes

4. ✅ **Test**
   - Run: `python3 tests/test_permission_fix.py`
   - Verify version: `2.1.1-with-permissions-fixed`

---

## 🆘 Still Not Working?

### Check NetSuite Execution Logs

1. Navigate to: **Customization → Scripting → Script Execution Log**
2. Filter by:
   - Script: User Search RESTlet
   - Type: Error
   - Date: Today
3. Look for errors in role search or permission queries

### Enable Debug Logging

Temporarily add to script (line 36):
```javascript
log.debug('enrichUsersWithRoles called', 'Internal IDs: ' + internalIds.join(','));
```

Then check execution logs for debug messages.

---

## 📊 Verification Commands

### Quick Version Check
```bash
python3 -c "from services.netsuite_client import NetSuiteClient; c=NetSuiteClient(); r=c.search_users('test', 'email', False); print(r['data']['metadata'].get('version'))"
```

### Full Test
```bash
python3 tests/test_permission_fix.py
```

### Check Roles for Specific User
```bash
python3 -c "
from services.netsuite_client import NetSuiteClient
import json
c = NetSuiteClient()
r = c.search_users('robin.turner@fivetran.com', 'email', True)
print('Roles:', r['data']['users'][0]['roles_count'])
print('Version:', r['data']['metadata']['version'])
"
```

**Expected:**
```
Roles: 3
Version: 2.1.1-with-permissions-fixed
```

---

## 💡 Tips

1. **Always check version** after deployment before running tests
2. **Wait 2-3 minutes** after clearing cache
3. **Use incognito window** to bypass browser cache
4. **Check execution logs** if errors occur
5. **Try new deployment** if cache issues persist

---

**Need more help?** The issue is likely one of:
- Script file not replaced correctly
- Deployment not set to "Released"
- NetSuite cache not cleared
- Wrong script ID in environment variable
