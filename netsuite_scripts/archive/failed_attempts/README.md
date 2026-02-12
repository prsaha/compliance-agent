# Failed Attempts

These versions attempted to fix role fetching but all failed.

## Timeline of Failures

### v2.0: user_search_restlet_with_permissions.js
- **Date:** 2026-02-11
- **Approach:** SuiteQL with EntityRole table
- **Error:** `INVALID_SEARCH_TYPE: EntityRole`
- **Result:** ❌ Script error, couldn't execute
- **Lesson:** EntityRole table doesn't exist or isn't accessible

### v2.1: user_search_restlet_with_permissions_v2.js
- **Date:** 2026-02-11
- **Approach:** Saved search with inactive filter
- **Error:** None (executed successfully)
- **Result:** ❌ 0 roles returned
- **Issue:** Inactive users filtered out, Robin Turner is inactive
- **Lesson:** Status filter was excluding test users

### v2.1.1: user_search_restlet_with_permissions_v2.1.js
- **Date:** 2026-02-11
- **Approach:** Saved search without inactive filter
- **Error:** None (executed successfully)
- **Result:** ❌ 0 roles returned
- **Issue:** Unknown, should have worked
- **Lesson:** Something else wrong with the implementation

### v3: user_search_restlet_v3_record_load.js
- **Date:** 2026-02-11
- **Approach:** record.load() to access employee record directly
- **Error:** None (executed successfully)
- **Result:** ❌ 0 roles returned
- **Issue:** 'roles' sublist returned 0 lines
- **Governance:** 10 units per user (expensive!)
- **Lesson:** Even direct record access didn't work

### v4: user_search_restlet_v4_final.js
- **Date:** 2026-02-11
- **Approach:** SuiteQL with employeeroles table
- **Error:** None (executed successfully)
- **Result:** ❌ Query returned 0 rows
- **Issue:** employeeroles table empty or wrong table name
- **Lesson:** SuiteQL employee-role queries don't work in this environment

## Root Cause

All v2-v4 attempts shared the same problem:
- **SuiteQL methods** for employee-role mapping don't work
- **EntityRole table** doesn't exist or isn't accessible
- **employeeroles table** returns no data
- **record.load() sublist** returns 0 lines

## The Solution (v5)

Returned to the **original proven method**:
- Use saved search with 'role' field
- Add GROUP summary
- This was working in v1.0 all along!

**Key Insight:** The original approach was correct. We just needed to:
1. Keep the saved search method for roles (working)
2. Add SuiteQL for permissions (also working)
3. Hybrid = Best of both worlds

## Why Keep These?

1. **Documentation:** Shows what doesn't work
2. **Troubleshooting:** If issues arise, we know what to avoid
3. **Learning:** Valuable lessons about NetSuite's quirks
4. **Evidence:** Proof that we tried multiple approaches

## Deployment Warning

⚠️ **DO NOT DEPLOY THESE FILES**

All versions v2.0 through v4.0 are non-functional. Use v5.0 (hybrid) instead.

---

**Total Time Spent:** ~4 hours debugging
**Final Working Solution:** v5.0 hybrid (saved search + SuiteQL)
**Lesson Learned:** Sometimes the original way is the right way!
