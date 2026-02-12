/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions (v3)
 *
 * Purpose: Search for specific users and return their roles and permissions
 *
 * v3 CHANGES:
 * - Uses record.load() instead of saved search for roles (more reliable)
 * - Guaranteed to work but uses more governance (~10 units per user)
 * - Still uses SuiteQL for permissions (efficient)
 *
 * Version: 3.0.0 (With record.load for roles)
 * Date: 2026-02-11
 */

define(['N/search', 'N/query', 'N/record', 'N/runtime', 'N/log'], function(search, query, record, runtime, log) {

    /**
     * Search for users by name or email
     */
    function post(requestBody) {
        const startTime = new Date().getTime();
        const script = runtime.getCurrentScript();
        const startingGovernance = script.getRemainingUsage();

        try {
            log.audit('User Search Request (v3.0)', JSON.stringify(requestBody));

            const searchType = requestBody.searchType || 'both';
            const searchValue = requestBody.searchValue;
            const includePermissions = requestBody.includePermissions !== false;
            const includeInactive = requestBody.includeInactive === true;

            if (!searchValue) {
                return {
                    success: false,
                    error: 'searchValue is required'
                };
            }

            // Search for users
            const users = searchUsers(searchValue, searchType, includeInactive);
            log.audit('Search Results', `Found ${users.length} user(s)`);

            // Fetch roles using record.load
            let enrichedUsers = users;
            if (users.length > 0) {
                enrichedUsers = enrichUsersWithRolesViaLoad(users);
            }

            // Fetch permissions if requested
            if (includePermissions && enrichedUsers.length > 0) {
                enrichedUsers = enrichUsersWithPermissions(enrichedUsers);
            }

            const endTime = new Date().getTime();
            const endingGovernance = script.getRemainingUsage();

            return {
                success: true,
                data: {
                    users: enrichedUsers,
                    metadata: {
                        search_value: searchValue,
                        search_type: searchType,
                        users_found: enrichedUsers.length,
                        execution_time_seconds: (endTime - startTime) / 1000,
                        timestamp: new Date().toISOString(),
                        version: '3.0.0-record-load'
                    },
                    governance: {
                        starting_units: startingGovernance,
                        ending_units: endingGovernance,
                        units_used: startingGovernance - endingGovernance,
                        units_per_user: enrichedUsers.length > 0 ?
                            ((startingGovernance - endingGovernance) / enrichedUsers.length).toFixed(2) : 0
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
     * Search for users
     */
    function searchUsers(searchValue, searchType, includeInactive) {
        const users = [];
        let filters = [];

        if (!includeInactive) {
            filters.push(['isinactive', 'is', 'F']);
        }

        if (filters.length > 0) {
            filters.push('AND');
        }

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
            users.push({
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
            });
            return true;
        });

        return users;
    }

    /**
     * Enrich users with roles using record.load() (v3 approach)
     * This is more expensive (10 units per user) but guaranteed to work
     */
    function enrichUsersWithRolesViaLoad(users) {
        try {
            log.audit('Fetching Roles via record.load', `For ${users.length} user(s)`);

            const enrichedUsers = [];

            for (var i = 0; i < users.length; i++) {
                const user = users[i];
                const roles = [];

                try {
                    // Load the employee record
                    const empRecord = record.load({
                        type: record.Type.EMPLOYEE,
                        id: user.internal_id,
                        isDynamic: false
                    });

                    // Get roles from the 'roles' sublist
                    const roleCount = empRecord.getLineCount({ sublistId: 'roles' });

                    log.audit('Role Count', `User ${user.name} (${user.internal_id}): ${roleCount} roles`);

                    for (var j = 0; j < roleCount; j++) {
                        try {
                            const roleId = empRecord.getSublistValue({
                                sublistId: 'roles',
                                fieldId: 'selectrecord',
                                line: j
                            });

                            const roleName = empRecord.getSublistText({
                                sublistId: 'roles',
                                fieldId: 'selectrecord',
                                line: j
                            });

                            if (roleId && roleName) {
                                roles.push({
                                    role_id: roleId.toString(),
                                    role_name: roleName,
                                    permissions: []
                                });
                            }
                        } catch (lineError) {
                            log.error(`Error reading role line ${j}`, lineError.toString());
                        }
                    }

                } catch (loadError) {
                    log.error(`Error loading employee ${user.internal_id}`, loadError.toString());
                }

                user.roles = roles;
                user.roles_count = roles.length;
                enrichedUsers.push(user);
            }

            log.audit('Roles Fetched', `${enrichedUsers.length} users processed`);

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
     * Enrich users with permissions using SuiteQL
     */
    function enrichUsersWithPermissions(users) {
        try {
            const allRoleIds = [];
            const roleIdSet = {};

            for (var i = 0; i < users.length; i++) {
                for (var j = 0; j < users[i].roles.length; j++) {
                    const roleId = users[i].roles[j].role_id;
                    if (!roleIdSet[roleId]) {
                        roleIdSet[roleId] = true;
                        allRoleIds.push(roleId);
                    }
                }
            }

            if (allRoleIds.length === 0) {
                log.audit('No roles to fetch permissions for');
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

            const queryResults = query.runSuiteQL({ query: sql }).asMappedResults();

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
                for (var p = 0; p < users[n].roles.length; p++) {
                    const role = users[n].roles[p];
                    role.permissions = permissionsByRole[role.role_id] || [];
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
            message: 'User Search RESTlet v3.0 (With record.load for roles) is active',
            version: '3.0.0-record-load',
            usage: {
                method: 'POST',
                example_request: {
                    searchType: 'email',
                    searchValue: 'john.doe@company.com',
                    includePermissions: true,
                    includeInactive: false
                }
            },
            changes: [
                'v3.0: Uses record.load() instead of saved search for roles',
                'v3.0: More governance (~10 units per user) but guaranteed to work',
                'v3.0: Still uses efficient SuiteQL for permissions'
            ]
        };
    }

    return {
        post: post,
        get: get
    };

});
