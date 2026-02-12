/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions (FIXED)
 *
 * Purpose: Search for specific users by name or email and return their roles and permissions
 *
 * FIXES:
 * - Now fetches actual role permissions using SuiteQL
 * - Batch fetches permissions for all roles at once (efficient)
 * - Includes governance monitoring
 * - Proper error handling
 *
 * Endpoints:
 *   POST - Search for users with filters
 *
 * Request Body:
 * {
 *   "searchType": "name" | "email" | "both",
 *   "searchValue": "John Doe" or "john.doe@company.com",
 *   "includePermissions": true/false,
 *   "includeInactive": false
 * }
 *
 * Version: 2.0.0 (With Permissions)
 * Date: 2026-02-11
 */

define(['N/search', 'N/query', 'N/runtime', 'N/log'], function(search, query, runtime, log) {

    /**
     * Search for users by name or email
     * @param {Object} requestBody
     * @returns {Object}
     */
    function post(requestBody) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('User Search Request (v2.0)', JSON.stringify(requestBody));

            // Extract parameters
            const searchType = requestBody.searchType || 'both';
            const searchValue = requestBody.searchValue;
            const includePermissions = requestBody.includePermissions !== false; // default true
            const includeInactive = requestBody.includeInactive === true; // default false

            // Validate required parameters
            if (!searchValue) {
                return {
                    success: false,
                    error: 'searchValue is required',
                    message: 'Please provide a name or email to search for'
                };
            }

            // Search for users
            const users = searchUsers(searchValue, searchType, includeInactive);

            log.audit('Search Results', `Found ${users.length} user(s)`);

            // Governance check after user search
            const afterUserSearch = script.getRemainingUsage();
            log.audit('Governance After User Search', `${afterUserSearch} units remaining`);

            // Fetch roles for all users
            let enrichedUsers = users;
            if (users.length > 0) {
                enrichedUsers = enrichUsersWithRoles(users);
            }

            // Fetch permissions if requested
            if (includePermissions && enrichedUsers.length > 0) {
                enrichedUsers = enrichUsersWithPermissions(enrichedUsers);
            }

            const endTime = new Date().getTime();
            const executionTime = (endTime - startTime) / 1000;
            const endingGovernance = script.getRemainingUsage();
            const governanceUsed = startingGovernance - endingGovernance;

            return {
                success: true,
                data: {
                    users: enrichedUsers,
                    metadata: {
                        search_value: searchValue,
                        search_type: searchType,
                        users_found: enrichedUsers.length,
                        execution_time_seconds: executionTime,
                        timestamp: new Date().toISOString(),
                        version: '2.0.0-with-permissions'
                    },
                    governance: {
                        starting_units: startingGovernance,
                        ending_units: endingGovernance,
                        units_used: governanceUsed,
                        units_per_user: enrichedUsers.length > 0 ? (governanceUsed / enrichedUsers.length).toFixed(2) : 0
                    }
                }
            };

        } catch (e) {
            log.error('User Search Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Failed to search for users'
            };
        }
    }

    /**
     * Search for users using saved search with wildcards
     * @param {string} searchValue - Name or email to search for
     * @param {string} searchType - 'name', 'email', or 'both'
     * @param {boolean} includeInactive - Include inactive users
     * @returns {Array} Array of user objects
     */
    function searchUsers(searchValue, searchType, includeInactive) {
        const users = [];

        // Create search filters using array syntax
        let filters = [];

        // Status filter (active/inactive)
        if (!includeInactive) {
            filters.push(['isinactive', 'is', 'F']);
        }

        // Add AND between status and search filters
        if (filters.length > 0) {
            filters.push('AND');
        }

        // Name or email filter
        if (searchType === 'name') {
            filters.push(['entityid', 'contains', searchValue]);
        } else if (searchType === 'email') {
            filters.push(['email', 'contains', searchValue]);
        } else { // 'both'
            // For 'both', use OR with array syntax
            filters.push([
                ['entityid', 'contains', searchValue],
                'OR',
                ['email', 'contains', searchValue]
            ]);
        }

        // Create employee search
        const userSearch = search.create({
            type: search.Type.EMPLOYEE,
            filters: filters,
            columns: [
                search.createColumn({ name: 'internalid' }),
                search.createColumn({ name: 'entityid' }),    // User ID/Name
                search.createColumn({ name: 'email' }),       // Email
                search.createColumn({ name: 'firstname' }),   // First Name
                search.createColumn({ name: 'lastname' }),    // Last Name
                search.createColumn({ name: 'title' }),       // Job Title
                search.createColumn({ name: 'department' }),  // Department
                search.createColumn({ name: 'subsidiary' }),  // Subsidiary
                search.createColumn({ name: 'isinactive' })   // Active Status
            ]
        });

        // Execute search
        userSearch.run().each(function(result) {
            const user = {
                user_id: result.getValue('entityid'),
                email: result.getValue('email'),
                first_name: result.getValue('firstname'),
                last_name: result.getValue('lastname'),
                name: `${result.getValue('firstname')} ${result.getValue('lastname')}`.trim(),
                title: result.getText('title') || null,
                department: result.getText('department') || null,
                subsidiary: result.getText('subsidiary') || null,
                is_active: result.getValue('isinactive') === 'F',
                internal_id: result.id
            };

            users.push(user);
            return true; // Continue processing
        });

        return users;
    }

    /**
     * Enrich users with their roles using batch query
     * @param {Array} users - Array of user objects
     * @returns {Array} Users with roles attached
     */
    function enrichUsersWithRoles(users) {
        try {
            // Extract internal IDs
            const internalIds = users.map(function(u) { return u.internal_id; });

            if (internalIds.length === 0) {
                return users;
            }

            log.audit('Fetching Roles', `For ${internalIds.length} user(s)`);

            // Batch query to get all user roles
            const sql =
                'SELECT ' +
                '    Employee.ID as internal_id, ' +
                '    EntityRole.Role as role_id, ' +
                '    Role.Name as role_name, ' +
                '    Role.IsInactive as role_inactive ' +
                'FROM Employee ' +
                'INNER JOIN EntityRole ON (EntityRole.Entity = Employee.ID) ' +
                'INNER JOIN Role ON (Role.ID = EntityRole.Role) ' +
                'WHERE Employee.ID IN (' + internalIds.join(',') + ') ' +
                'AND Role.IsInactive = \'F\' ' +
                'ORDER BY Employee.ID, Role.Name';

            const queryResults = query.runSuiteQL({
                query: sql
            }).asMappedResults();

            log.audit('Roles Fetched', `${queryResults.length} role assignments found`);

            // Group roles by user internal ID
            const rolesByUser = {};
            for (var i = 0; i < queryResults.length; i++) {
                const result = queryResults[i];
                const internalId = result.internal_id.toString();

                if (!rolesByUser[internalId]) {
                    rolesByUser[internalId] = [];
                }

                rolesByUser[internalId].push({
                    role_id: result.role_id.toString(),
                    role_name: result.role_name,
                    permissions: []  // Will be filled later if includePermissions=true
                });
            }

            // Attach roles to users
            const enrichedUsers = [];
            for (var j = 0; j < users.length; j++) {
                const user = users[j];
                const userRoles = rolesByUser[user.internal_id] || [];

                user.roles = userRoles;
                user.roles_count = userRoles.length;

                enrichedUsers.push(user);
            }

            return enrichedUsers;

        } catch (e) {
            log.error('Error enriching users with roles', e.toString());
            // Return users without roles on error
            return users.map(function(u) {
                u.roles = [];
                u.roles_count = 0;
                return u;
            });
        }
    }

    /**
     * Enrich users with role permissions using batch query (FIXED)
     * @param {Array} users - Array of user objects with roles
     * @returns {Array} Users with permissions attached to roles
     */
    function enrichUsersWithPermissions(users) {
        try {
            // Collect all unique role IDs across all users
            const allRoleIds = [];
            const roleIdSet = {};

            for (var i = 0; i < users.length; i++) {
                const user = users[i];
                for (var j = 0; j < user.roles.length; j++) {
                    const roleId = user.roles[j].role_id;
                    if (!roleIdSet[roleId]) {
                        roleIdSet[roleId] = true;
                        allRoleIds.push(roleId);
                    }
                }
            }

            if (allRoleIds.length === 0) {
                log.audit('No roles to fetch permissions for', 'Returning users as-is');
                return users;
            }

            log.audit('Fetching Permissions', `For ${allRoleIds.length} unique role(s)`);

            // Build role ID list for SQL IN clause
            // Need to handle both numeric and string role IDs
            const roleIdList = [];
            for (var k = 0; k < allRoleIds.length; k++) {
                const roleId = allRoleIds[k].toString();
                // For numeric IDs, use as-is; for custom roles, wrap in quotes
                if (roleId.indexOf('customrole') === 0) {
                    roleIdList.push("'" + roleId + "'");
                } else {
                    roleIdList.push(roleId);
                }
            }

            // Batch query to get all permissions for all roles
            const sql =
                'SELECT ' +
                '    Role.ID AS role_id, ' +
                '    RolePermissions.PermKey AS permission_key, ' +
                '    RolePermissions.Name AS permission_name, ' +
                '    BUILTIN.DF(RolePermissions.PermLevel) AS permission_level ' +
                'FROM Role ' +
                'INNER JOIN RolePermissions ON (RolePermissions.Role = Role.ID) ' +
                'WHERE Role.ID IN (' + roleIdList.join(',') + ') ' +
                'AND Role.IsInactive = \'F\'';

            const queryResults = query.runSuiteQL({
                query: sql
            }).asMappedResults();

            log.audit('Permissions Fetched', `${queryResults.length} permissions found`);

            // Group permissions by role ID
            const permissionsByRole = {};
            for (var m = 0; m < queryResults.length; m++) {
                const result = queryResults[m];
                const roleId = result.role_id.toString();

                if (!permissionsByRole[roleId]) {
                    permissionsByRole[roleId] = [];
                }

                permissionsByRole[roleId].push({
                    key: result.permission_key,
                    permission: result.permission_key,
                    permission_name: result.permission_name,
                    level: result.permission_level
                });
            }

            // Attach permissions to user roles
            for (var n = 0; n < users.length; n++) {
                const user = users[n];
                for (var p = 0; p < user.roles.length; p++) {
                    const role = user.roles[p];
                    const roleId = role.role_id;
                    role.permissions = permissionsByRole[roleId] || [];
                    role.permission_count = role.permissions.length;
                }
            }

            return users;

        } catch (e) {
            log.error('Error enriching users with permissions', e.toString());
            log.error('Error details', JSON.stringify({
                message: e.message,
                name: e.name,
                stack: e.stack
            }));
            // Return users with roles but no permissions on error
            return users;
        }
    }

    /**
     * GET handler for testing
     */
    function get(requestParams) {
        return {
            success: true,
            message: 'User Search RESTlet v2.0 (With Permissions) is active',
            version: '2.0.0-with-permissions',
            usage: {
                method: 'POST',
                example_request: {
                    searchType: 'email',
                    searchValue: 'john.doe@company.com',
                    includePermissions: true,
                    includeInactive: false
                }
            },
            fixes: [
                'Now fetches actual role permissions using SuiteQL',
                'Batch fetches permissions for efficiency',
                'Includes governance monitoring',
                'Proper error handling and logging'
            ]
        };
    }

    return {
        post: post,
        get: get
    };

});
