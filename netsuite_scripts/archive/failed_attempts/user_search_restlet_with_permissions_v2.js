/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions (FIXED v2)
 *
 * Purpose: Search for specific users by name or email and return their roles and permissions
 *
 * FIXES v2:
 * - Fixed SuiteQL query (EntityRole is not a valid table)
 * - Uses saved search for role lookup (more reliable)
 * - Uses SuiteQL for permissions (works correctly)
 * - Proper error handling
 *
 * Version: 2.1.0 (With Permissions - Fixed)
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
            log.audit('User Search Request (v2.1)', JSON.stringify(requestBody));

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
                        version: '2.1.0-with-permissions-fixed'
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
            log.error('Error Stack', JSON.stringify({
                type: e.type,
                name: e.name,
                message: e.message,
                stack: e.stack
            }));
            return {
                success: false,
                error: e.toString(),
                message: 'Failed to search for users',
                details: {
                    type: e.type,
                    name: e.name
                }
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
                search.createColumn({ name: 'entityid' }),
                search.createColumn({ name: 'email' }),
                search.createColumn({ name: 'firstname' }),
                search.createColumn({ name: 'lastname' }),
                search.createColumn({ name: 'title' }),
                search.createColumn({ name: 'department' }),
                search.createColumn({ name: 'subsidiary' }),
                search.createColumn({ name: 'isinactive' })
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
            return true;
        });

        return users;
    }

    /**
     * Enrich users with their roles using saved search (FIXED)
     * Uses saved search instead of SuiteQL because EntityRole is not a valid table
     *
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

            // Use saved search to get roles for all users at once
            const roleSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    ['internalid', 'anyof', internalIds],
                    'AND',
                    ['isinactive', 'is', 'F']
                ],
                columns: [
                    search.createColumn({ name: 'internalid' }),
                    search.createColumn({
                        name: 'role',
                        summary: search.Summary.GROUP
                    })
                ]
            });

            // Group roles by user internal ID
            const rolesByUser = {};

            roleSearch.run().each(function(result) {
                const internalId = result.getValue({ name: 'internalid' });
                const roleId = result.getValue({
                    name: 'role',
                    summary: search.Summary.GROUP
                });
                const roleName = result.getText({
                    name: 'role',
                    summary: search.Summary.GROUP
                });

                if (!rolesByUser[internalId]) {
                    rolesByUser[internalId] = [];
                }

                if (roleId && roleName) {
                    // Check for duplicates
                    const exists = rolesByUser[internalId].some(function(r) {
                        return r.role_id === roleId;
                    });

                    if (!exists) {
                        rolesByUser[internalId].push({
                            role_id: roleId.toString(),
                            role_name: roleName,
                            permissions: []
                        });
                    }
                }

                return true;
            });

            log.audit('Roles Fetched', `${Object.keys(rolesByUser).length} users with roles`);

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
            log.error('Error details', JSON.stringify({
                type: e.type,
                name: e.name,
                message: e.message
            }));
            // Return users without roles on error
            return users.map(function(u) {
                u.roles = [];
                u.roles_count = 0;
                return u;
            });
        }
    }

    /**
     * Enrich users with role permissions using SuiteQL
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
            const roleIdList = [];
            for (var k = 0; k < allRoleIds.length; k++) {
                const roleId = allRoleIds[k].toString();
                // For custom roles, wrap in quotes; for numeric, use as-is
                if (roleId.indexOf('customrole') === 0) {
                    roleIdList.push("'" + roleId + "'");
                } else {
                    roleIdList.push(roleId);
                }
            }

            // Use SuiteQL to fetch permissions (this works correctly)
            // Note: We're querying the Role and RolePermissions tables directly
            const sql =
                'SELECT ' +
                '    r.id AS role_id, ' +
                '    rp.permkey AS permission_key, ' +
                '    rp.name AS permission_name, ' +
                '    BUILTIN.DF(rp.permlevel) AS permission_level ' +
                'FROM ' +
                '    Role r ' +
                'INNER JOIN ' +
                '    RolePermissions rp ON rp.role = r.id ' +
                'WHERE ' +
                '    r.id IN (' + roleIdList.join(',') + ') ' +
                '    AND r.isinactive = \'F\'';

            log.audit('SuiteQL Query', sql);

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
                type: e.type,
                name: e.name,
                message: e.message,
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
            message: 'User Search RESTlet v2.1 (With Permissions - Fixed) is active',
            version: '2.1.0-with-permissions-fixed',
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
                'v2.0: Added permission fetching via SuiteQL',
                'v2.1: Fixed EntityRole error - now uses saved search for roles',
                'v2.1: SuiteQL only used for permissions (which works correctly)',
                'v2.1: Improved error handling and logging'
            ]
        };
    }

    return {
        post: post,
        get: get
    };

});
