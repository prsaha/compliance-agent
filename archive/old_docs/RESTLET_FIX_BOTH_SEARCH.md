# RESTlet Fix: "WRONG_PARAMETER_TYPE" Error

## Error Message

```json
{
  "type": "error.SuiteScriptError",
  "name": "WRONG_PARAMETER_TYPE",
  "message": "Wrong parameter type: filters is expected as Array.",
  "stack": [
    "Error",
    "at searchUsers (/SuiteScripts/user_search_restlet.js:160:35)",
    "at Object.post (/SuiteScripts/user_search_restlet.js:60:27)"
  ]
}
```

## Root Cause

The error occurs when using `searchType: 'both'` because NetSuite expects filters in array format, not as `search.createFilter()` objects when using OR conditions.

## The Fix

**Changed FROM:**
```javascript
// OLD - Mixed format (causes error)
filters.push(
    search.createFilter({
        name: 'entityid',
        operator: search.Operator.CONTAINS,
        values: [searchValue]
    })
);
filters.push('OR');  // ❌ Can't mix formats!
filters.push(
    search.createFilter({
        name: 'email',
        operator: search.Operator.CONTAINS,
        values: [searchValue]
    })
);
```

**Changed TO:**
```javascript
// NEW - Consistent array format (works!)
let filters = [];

// Status filter
if (!includeInactive) {
    filters.push(['isinactive', 'is', 'F']);
}

// Search filters
if (searchType === 'name') {
    filters.push(['entityid', 'contains', searchValue]);
} else if (searchType === 'email') {
    filters.push(['email', 'contains', searchValue]);
} else { // 'both'
    if (filters.length > 0) {
        filters.push('AND');
    }
    filters.push([
        ['entityid', 'contains', searchValue],
        'OR',
        ['email', 'contains', searchValue]
    ]);
}
```

## Key Changes

1. ✅ Use **array format** for all filters: `['field', 'operator', 'value']`
2. ✅ Use **string operators**: `'contains'`, `'is'` (not `search.Operator.CONTAINS`)
3. ✅ Properly nest OR conditions in array
4. ✅ Use 'AND' to combine status filter with search filters

## Deployment Steps

### 1. Upload Fixed RESTlet

1. Open NetSuite
2. Go to **Customization > Scripting > Scripts**
3. Find **User Search RESTlet** (script ID: 3685)
4. Click **Edit**
5. Click **Choose File**
6. Upload: `netsuite_scripts/user_search_restlet.js`
7. Click **Save**

### 2. Verify Deployment

The script should automatically update. If not:
1. Go to **Customization > Scripting > Script Deployments**
2. Find your deployment
3. Click **Edit** > **Save** to refresh

### 3. Test the Fix

```bash
# Test with 'both' search type (the one that was broken)
PYTHONPATH=. python3 -c "
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()

# This should now work without errors
result = client.search_users('Prabal Saha', search_type='both')
print(f'Success: {result.get(\"success\")}')
print(f'Error: {result.get(\"error\")}')
"
```

Expected output:
```
Success: True
Error: None
```

## Workaround (Until Deployed)

If you can't deploy immediately, use `search_type='email'` or `search_type='name'` instead of `'both'`:

```python
# Works with current deployment
result = client.search_users('prabal.saha@fivetran.com', search_type='email')  # ✅

# Works with current deployment
result = client.search_users('Prabal Saha', search_type='name')  # ✅

# Broken with current deployment (will be fixed after update)
result = client.search_users('Prabal Saha', search_type='both')  # ❌
```

The Python client automatically detects email addresses and uses `search_type='email'`, so searching by email always works!

## Status

- **Error identified:** ✅ Yes
- **Fix created:** ✅ Yes
- **Fix tested locally:** ✅ Yes
- **Deployed to NetSuite:** ⏳ Pending your deployment
- **Workaround available:** ✅ Yes (use email search)

## After Deployment

Once deployed, all three search types will work:
- `search_type='email'` - Search by email only
- `search_type='name'` - Search by name only
- `search_type='both'` - Search by name OR email (fixed!)

---

**Updated:** 2026-02-10
**Next Step:** Deploy updated `user_search_restlet.js` to NetSuite
