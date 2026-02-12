/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions (FIXED v2.1)
 *
 * Purpose: Search for specific users by name or email and return their roles and permissions
 *
 * FIXES v2.1.1:
 * - Removed inactive filter from role search (was excluding inactive users' roles)
 * - Now fetches roles for all users regardless of active status
 *
 * Version: 2.1.1 (With Permissions - Fixed Inactive Users)
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
            log.audit('User Search Request (v2.1.1)', JSON.stringify(requestBody));

            // Extract parameters
            const searchType = requestBody.searchType || 'both';
            const searchValue = requestBody.searchValue;
            const includePermissions = requestBody.includePermissions !== false;
            const includeInactive = requestBody.includeInactive === true;

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

            // Governance check
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
                        version: '2.1.1-with-permissions-fixed'
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
     */
    function searchUsers(searchValue, searchType, includeInactive) {
        const users = [];
        let filters = [];

        // Status filter
        if (!includeInactive) {
            filters.push(['isinactive', 'is', 'F']);
        }

        if (filters.length > 0) {
            filters.push('AND');
        }

        // Name or email filter
        if (searchType === 'name') {
            filters.push(['entityid', 'contains', searchValue]);
        } else if (searchType === 'email') {
            filters.push(['email', 'contains', searchValue]);
        } else {
            filters.push([
                ['entityid', 'contains', searchValue],
                'OR',
                ['email', 'contains', searchValue]
            ]);
        }

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
     * Enrich users with their roles using saved search (FIXED v2.1.1)
     * IMPORTANT: Removed inactive filter so we get roles for ALL users
     */
    function enrichUsersWithRoles(users) {
        try {
            const internalIds = users.map(function(u) { return u.internal_id; });

            if (internalIds.length === 0) {
                return users;
            }

            log.audit('Fetching Roles', `For ${internalIds.length} user(s)`);

            // FIXED: Removed isinactive filter - we want roles for all users
            const roleSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    ['internalid', 'anyof', internalIds]
                    // ✅ Removed: 'AND', ['isinactive', 'is', 'F']
                ],
                columns: [
                    search.createColumn({ name: 'internalid' }),
                    search.createColumn({
                        name: 'role',
                        summary: search.Summary.GROUP
                    })
                ]
            });

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
            return users.map(function(u) {
                u.roles = [];
                u.roles_count = 0;
                return u;
            });
        }
    }

    /**
     * Enrich users with role permissions using SuiteQL
     */
    function enrichUsersWithPermissions(users) {
        try {
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

            const roleIdList = [];
            for (var k = 0; k < allRoleIds.length; k++) {
                const roleId = allRoleIds[k].toString();
                if (roleId.indexOf('customrole') === 0) {
                    roleIdList.push("'" + roleId + "'");
                } else {
                    roleIdList.push(roleId);
                }
            }

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
                '    r.id IN (' + roleIdList.join(',') + ')';
                // Note: Removed r.isinactive filter - permissions are same for active/inactive roles

            log.audit('SuiteQL Query', sql);

            const queryResults = query.runSuiteQL({
                query: sql
            }).asMappedResults();

            log.audit('Permissions Fetched', `${queryResults.length} permissions found`);

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
            return users;
        }
    }

    /**
     * GET handler for testing
     */
    function get(requestParams) {
        return {
            success: true,
            message: 'User Search RESTlet v2.1.1 (With Permissions - Fixed Inactive Users) is active',
            version: '2.1.1-with-permissions-fixed',
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
                'v2.1.1: Fixed inactive user bug - now fetches roles for inactive users too'
            ]
        };
    }

    return {
        post: post,
        get: get
    };

});
