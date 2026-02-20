---
name: employee-onboarding
description: Multi-system employee onboarding workflow across Okta, Workday, Celigo, and NetSuite. Use when onboarding a new hire, provisioning system access for a new employee, enabling a user in NetSuite, assigning roles to a new team member, or checking onboarding status. Handles two paths: standard onboarding (provision and enable) and superuser onboarding (provision + create approval ticket for elevated role assignment). Automatically runs SOD compliance check before any role assignment. Requires compliance MCP server at localhost:8080.
metadata:
  author: Prabal Saha
  version: 1.0.0
  mcp-server: compliance-system
---

# Employee Onboarding Skill

## Instructions

This skill orchestrates new employee provisioning across four systems in sequence:
Okta → Workday → Celigo → NetSuite

Two paths exist based on access level:
- **Standard user**: provision across all systems, enable in NetSuite with standard roles
- **Superuser**: same provisioning + create a Jira ticket for elevated role assignment and manual NetSuite enablement by an admin

Always run an SOD compliance check before assigning any roles. Never assign roles that create
CRITICAL or HIGH violations without an approved exception.

Consult `references/system-guide.md` for API details, field mappings, and error codes per system.
Consult `references/role-matrix.md` for standard role sets by job title and department.

---

### Step 0: Gather Required Information

Before starting, confirm you have:
- Full legal name
- Work email address
- Job title
- Department
- Manager name or email
- Start date
- Access level: **standard** or **superuser**

If any of these are missing, ask before proceeding. Do not start provisioning with incomplete data.

---

### Step 1: Okta — Identity Provisioning

Okta is the identity provider. All downstream systems depend on the Okta identity being created first.

**Actions:**
1. Create the user in Okta with:
   - `login`: work email
   - `firstName`, `lastName`: from intake
   - `title`: job title
   - `department`: department
   - `manager`: manager's email
   - `userType`: `standard` or `superuser`
2. Assign the user to the appropriate Okta groups based on department (see `references/role-matrix.md` for group mappings)
3. Send activation email: set `sendEmail: true`
4. Capture the Okta `userId` — required for all downstream steps

**Verify:** Call Okta GET `/api/v1/users/{userId}` — status should be `PROVISIONED`.

**If Okta creation fails:**
- Duplicate email: check if user already exists (`GET /api/v1/users?q={email}`)
- Invalid department: refer to `references/role-matrix.md` for valid department values
- Do not proceed to Step 2 until Okta status is `PROVISIONED`

---

### Step 2: Workday — HR Record Creation

Workday is the system of record for employment data. The Okta userId is linked here.

**Actions:**
1. Create the worker record in Workday with:
   - Employee ID (auto-assigned by Workday)
   - Legal name, start date, job title, department, cost center
   - Manager (look up by email in Workday)
   - `externalId`: Okta `userId` from Step 1
2. Set employment status to `Active`
3. Capture the Workday `workerId` — used by Celigo for sync

**Verify:** Confirm worker record exists and status is `Active`.

**If Workday creation fails:**
- Manager not found: verify manager has an active Workday record
- Cost center invalid: check with Finance for the correct cost center code
- Do not proceed until Workday record is confirmed active

---

### Step 3: Celigo — Sync to NetSuite

Celigo is the integration layer that syncs the Workday record to NetSuite. This is typically automatic but can be triggered manually.

**Actions:**
1. Trigger the Workday → NetSuite employee sync flow in Celigo:
   - Flow name: `Workday Employee to NetSuite Contact/Employee`
   - Filter: `workerId = {workerId from Step 2}`
2. Monitor the sync run — wait for status `success` (typically 2-5 minutes)
3. Capture the NetSuite `employeeId` from the Celigo sync result

**Verify:** Confirm the sync run completed with 0 errors and the NetSuite employee record was created.

**If Celigo sync fails:**
- Field mapping error: check `references/system-guide.md` for required NetSuite field formats
- Duplicate record: search NetSuite for existing employee by email before re-running
- Auth error: verify Celigo connection credentials for NetSuite are valid

---

### Step 4: NetSuite — Role Assignment and Enablement

This step differs based on access level.

---

#### Path A: Standard User

**Actions:**
1. Look up the employee in NetSuite by email: call `get_user_violations(user_identifier={email})` — this confirms the record exists and returns the internal user ID
2. Determine the standard role set for this job title and department: call `recommend_roles_for_job_title(job_title={title}, department={department})`
3. Run SOD compliance check on the recommended roles: call `analyze_access_request(user_id={id}, requested_role={each role}, include_existing_roles=true)`
4. If all roles are CLEAR or LOW risk: assign roles directly in NetSuite via `validate_job_role`
5. Enable the user in NetSuite: set `isInactive: false`
6. Confirm enablement: call `get_user_violations(user_identifier={email})` — user should appear as active with assigned roles

**Verify:** User can log in to NetSuite. Status is active. Roles match the approved set.

---

#### Path B: Superuser

Superusers require elevated roles (e.g., Administrator, Controller, Full Access) that must go through an approval workflow before NetSuite enablement.

**Actions:**
1. Look up the employee in NetSuite: call `get_user_violations(user_identifier={email})`
2. Identify the requested elevated roles from intake data
3. Run SOD compliance check on ALL requested roles together: call `analyze_access_request(user_id={id}, requested_role={roles}, include_existing_roles=true)`
4. Create a Jira ticket with the following pre-filled:

```
Summary: [SUPERUSER ONBOARDING] Role assignment request — {full name}
Description:
  Employee: {name}
  Email: {email}
  Job Title: {title}
  Department: {department}
  Start Date: {start date}
  Manager: {manager}

  Requested Roles:
  {list each role}

  SOD Compliance Check Result:
  {paste analyze_access_request output — violations if any, CLEAR if none}

  Required Action:
  1. Review role list against job responsibilities
  2. Approve or modify role assignment
  3. Enable user in NetSuite (set isInactive: false)
  4. Assign approved roles in NetSuite
  5. Close this ticket

Assignee: IT Security / NetSuite Admin
Priority: High (block on start date: {start date})
Labels: onboarding, superuser, netsuite-access
```

5. Do NOT enable the user in NetSuite at this step — leave account inactive until ticket is resolved
6. Notify the manager that provisioning is complete pending IT approval, with the Jira ticket link

---

### Step 5: Onboarding Summary

After completing all steps, provide a summary:

```
ONBOARDING COMPLETE — {full name}

Okta:     PROVISIONED  ({userId})
Workday:  ACTIVE       ({workerId})
Celigo:   SYNCED       (sync run {runId})
NetSuite: {ENABLED with roles / PENDING — Jira {ticket-id}}

Start date: {date}
Manager: {manager}
Access level: {standard / superuser}
```

If any step is incomplete, list it clearly with the blocking reason and next action required.

---

### Offboarding Note

This skill handles onboarding only. For offboarding (account deactivation, role removal, access revocation), a separate workflow is required. Do not attempt to reverse these steps manually.

---

## Examples

### Example 1: Standard user onboarding

User says: "Onboard Sarah Chen, sarah.chen@celigo.com, Senior Accountant, Finance, starts March 1, reports to Mike Torres"

Actions:
1. Create Okta identity → `PROVISIONED`
2. Create Workday record → `Active`, workerId: `WD-48291`
3. Trigger Celigo sync → success, netsuiteId: `NS-10847`
4. `recommend_roles_for_job_title("Senior Accountant", "Finance")` → AP Processor, GL Viewer
5. `analyze_access_request` → CLEAR (no SOD violations)
6. Assign roles, enable in NetSuite
7. Summary: all systems green, user active

---

### Example 2: Superuser onboarding

User says: "Onboard James Rivera, james.rivera@celigo.com, IT Systems Admin, IT, superuser, starts Feb 24"

Actions:
1-3: Same provisioning flow as above
4. `analyze_access_request` for Administrator + Script Deploy roles → HIGH risk (Script Dev vs Production conflict)
5. Create Jira ticket `NS-ONBOARD-2847` with SOD check results pre-filled
6. NetSuite account left inactive
7. Notify manager: "Provisioning complete. NetSuite access pending IT approval — see NS-ONBOARD-2847"

---

## Troubleshooting

**Okta user stuck in STAGED (not PROVISIONED)**
Cause: Activation email not sent or group assignment failed.
Solution: Manually trigger activation via Okta admin console or re-send activation email.

**Celigo sync completes but NetSuite record not found**
Cause: Sync created a Contact record instead of Employee record (field mapping issue).
Solution: Check Celigo flow field mapping for `employeeType`; ensure it maps to `Employee` not `Contact`.

**SOD check returns violations for standard roles**
Cause: Role set for job title has a built-in conflict (role definition issue, not user issue).
Solution: Call `get_role_conflicts({role})` to identify the conflict, then escalate to NetSuite admin to fix the role definition. Do not assign conflicting roles.

**Jira ticket creation fails**
Cause: Jira API credentials expired or project key incorrect.
Solution: Check `references/system-guide.md` for current Jira project key and auth token rotation schedule.

**User reports cannot log in to NetSuite after standard onboarding**
Cause: User is still set to inactive in NetSuite despite enablement step.
Solution: Call `get_user_violations(user_identifier={email})` to check current status; if inactive, re-trigger enablement.
