# NetSuite RESTlet Archive

This directory contains archived versions of NetSuite RESTlets for historical reference.

## 📁 Directory Structure

```
archive/
├── original_versions/      # Original working versions (v1.0)
└── failed_attempts/        # Failed iterations (v2.0 - v4.0)
```

## 📋 Why These Are Archived

### Original Versions
These are the first versions that were working, before optimization and fixes.
- **Kept for:** Historical reference, rollback if needed
- **Status:** Functional but not optimized

### Failed Attempts
These versions attempted various approaches to fetch roles but all failed.
- **Kept for:** Learning what doesn't work, troubleshooting reference
- **Status:** Non-functional (returned 0 roles)

## ✅ Current Production Versions

Located in parent directory (`netsuite_scripts/`):

| File | Version | Purpose | Status |
|------|---------|---------|--------|
| **sod_users_roles_restlet_optimized.js** | v2.1 | Bulk user sync | ✅ Production |
| **user_search_restlet_v5_hybrid.js** | v5.0 | User search | ✅ Production |

## 🚫 Do Not Deploy Archived Versions

The files in this archive are for reference only. Always deploy from the parent directory.

---

**Last Updated:** 2026-02-11
**Cleaned By:** Automated cleanup script
