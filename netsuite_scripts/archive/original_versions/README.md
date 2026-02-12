# Original Versions

These are the first working versions before optimization.

## Files

### sod_users_roles_restlet.js
- **Version:** 1.0.0
- **Date:** 2026-02-09
- **Status:** Functional but slow
- **Issue:** Hit governance limits (5000 units)
- **Method:** Individual searches for each user's roles
- **Performance:** ~100 units per user

### user_search_restlet.js
- **Version:** 1.0.0
- **Date:** 2026-02-10
- **Status:** Functional, gets role names
- **Issue:** Didn't fetch permissions (returned empty array)
- **Method:** Saved search with 'role' field
- **Note:** This method was actually working for roles! We returned to this approach in v5.

## Why Archived

These versions were replaced with optimized versions:
- **v1.0 → v2.1 (bulk):** Added SuiteQL optimizations, governance monitoring
- **v1.0 → v5.0 (search):** Added permission fetching

## Historical Value

The original `user_search_restlet.js` saved search method became the basis for:
- v5 hybrid search RESTlet (working)
- v2.1 bulk RESTlet fix (working)

**Lesson:** The original approach was correct! We just needed to add permission fetching.
