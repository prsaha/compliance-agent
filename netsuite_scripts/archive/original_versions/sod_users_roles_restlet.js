/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * SOD Compliance - Users & Roles Data Collection RESTlet
 *
 * Purpose: Fetch all active users with their assigned roles and permissions
 * for SOD (Segregation of Duties) compliance analysis
 *
 * Endpoints:
 *   GET - Fetch users and roles
 *   POST - Fetch with filters (body params)
 *
 * Usage:
 *   GET  https://[account].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXX&deploy=1
 *   POST https://[account].restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXX&deploy=1
 *        Body: { "subsidiary": "US", "department": "Finance", "limit": 100, "offset": 0 }
 */

define(['N/search', 'N/record', 'N/query'], function(search, record, query) {
    /**
     * GET handler - Fetch users and their roles
     * @param {Object} requestParams - Query parameters
     * @returns {Object} Users data with roles and permissions
     */
    function doGet(requestParams) {
        try {
            log.audit('SOD Data Collection', 'GET request started');

            var filters = {
                status: requestParams.status || 'ACTIVE',
                subsidiary: requestParams.subsidiary || null,
                department: requestParams.department || null,
                limit: parseInt(requestParams.limit) || 1000,
                offset: parseInt(requestParams.offset) || 0
            };

            return fetchUsersAndRoles(filters);

        } catch (e) {
            log.error('GET Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Error fetching users and roles'
            };
        }
    }

    /**
     * POST handler - Fetch users with filters in body
     * @param {Object} requestBody - Request body with filters
     * @returns {Object} Users data with roles and permissions
     */
    function doPost(requestBody) {
        try {
            log.audit('SOD Data Collection', 'POST request started');

            var filters = {
                status: requestBody.status || 'ACTIVE',
                subsidiary: requestBody.subsidiary || null,
                department: requestBody.department || null,
                limit: parseInt(requestBody.limit) || 1000,
                offset: parseInt(requestBody.offset) || 0,
                includePermissions: requestBody.includePermissions !== false, // default true
                includeInactive: requestBody.includeInactive === true // default false
            };

            return fetchUsersAndRoles(filters);

        } catch (e) {
            log.error('POST Error', e.toString());
            return {
                success: false,
                error: e.toString(),
                message: 'Error fetching users and roles'
            };
        }
    }

    /**
     * Main function to fetch users and their roles
     * @param {Object} filters - Filter criteria
     * @returns {Object} Structured user data
     */
    function fetchUsersAndRoles(filters) {
        var startTime = new Date().getTime();

        // Build user search
        var userSearchFilters = buildUserFilters(filters);
        var users = searchUsers(userSearchFilters, filters.limit, filters.offset);

        log.audit('Users Found', users.length + ' users retrieved');

        // Enrich users with roles and permissions
        var enrichedUsers = [];
        for (var i = 0; i < users.length; i++) {
            try {
                var user = users[i];

                // Skip users without valid ID
                if (!user || !user.id) {
                    log.error('Skipping user with invalid ID', 'Index: ' + i);
                    continue;
                }

                var roles = getUserRoles(user.id);

                if (filters.includePermissions) {
                    // Get detailed permissions for each role
                    roles = enrichRolesWithPermissions(roles);
                }

                enrichedUsers.push({
                    user_id: user.id,
                    internal_id: user.internalId,
                    name: user.name,
                    email: user.email,
                    employee_id: user.employeeId,
                    status: user.status,
                    subsidiary: user.subsidiary,
                    department: user.department,
                    last_login: user.lastLogin,
                    roles: roles || [],  // Ensure roles is always an array
                    roles_count: (roles || []).length,
                    synced_at: new Date().toISOString()
                });

            } catch (e) {
                log.error('Error processing user', (user ? user.id : 'unknown') + ': ' + e.toString());
                // Continue processing other users
            }
        }

        var endTime = new Date().getTime();
        var executionTime = (endTime - startTime) / 1000;

        // Get total count for pagination
        var totalUsers = getTotalUserCount(userSearchFilters);

        return {
            success: true,
            data: {
                users: enrichedUsers,
                metadata: {
                    total_users: totalUsers,
                    returned_count: enrichedUsers.length,
                    limit: filters.limit,
                    offset: filters.offset,
                    has_more: (filters.offset + enrichedUsers.length) < totalUsers,
                    filters_applied: filters,
                    execution_time_seconds: executionTime,
                    timestamp: new Date().toISOString()
                }
            }
        };
    }

    /**
     * Build search filters for users
     * @param {Object} filters - Filter criteria
     * @returns {Array} NetSuite search filters
     */
    function buildUserFilters(filters) {
        var searchFilters = [];

        // Status filter - default to ACTIVE users only
        if (!filters.includeInactive) {
            if (filters.status === 'INACTIVE') {
                searchFilters.push(search.createFilter({
                    name: 'isinactive',
                    operator: search.Operator.IS,
                    values: ['T']
                }));
            } else {
                // Default: show only ACTIVE users
                searchFilters.push(search.createFilter({
                    name: 'isinactive',
                    operator: search.Operator.IS,
                    values: ['F']
                }));
            }
        }
        // If includeInactive is true, don't add any status filter (show all)

        // Subsidiary filter
        if (filters.subsidiary) {
            searchFilters.push(search.createFilter({
                name: 'name',
                join: 'subsidiary',
                operator: search.Operator.IS,
                values: [filters.subsidiary]
            }));
        }

        // Department filter
        if (filters.department) {
            searchFilters.push(search.createFilter({
                name: 'name',
                join: 'department',
                operator: search.Operator.IS,
                values: [filters.department]
            }));
        }

        return searchFilters;
    }

    /**
     * Search for users
     * @param {Array} filters - Search filters
     * @param {Number} limit - Result limit
     * @param {Number} offset - Result offset
     * @returns {Array} User records
     */
    function searchUsers(filters, limit, offset) {
        var users = [];

        var userSearch = search.create({
            type: search.Type.EMPLOYEE,
            filters: filters,
            columns: [
                search.createColumn({ name: 'internalid' }),
                search.createColumn({ name: 'entityid' }),
                search.createColumn({ name: 'firstname' }),
                search.createColumn({ name: 'lastname' }),
                search.createColumn({ name: 'email' }),
                search.createColumn({ name: 'isinactive' }),
                search.createColumn({ name: 'subsidiary' }),
                search.createColumn({ name: 'department' }),
                search.createColumn({ name: 'lastmodifieddate' })
            ]
        });

        // Use paged search for better performance
        var pagedData = userSearch.runPaged({ pageSize: 1000 });
        var pageIndex = Math.floor(offset / 1000);

        if (pageIndex < pagedData.pageRanges.length) {
            var page = pagedData.fetch({ index: pageIndex });

            page.data.forEach(function(result) {
                var isInactive = result.getValue('isinactive');
                // Handle different formats: 'F'/'T', false/true, 'false'/'true'
                var status = (isInactive === false || isInactive === 'F' || isInactive === 'false') ? 'ACTIVE' : 'INACTIVE';

                users.push({
                    id: result.getValue('entityid'),
                    internalId: result.getValue('internalid'),
                    name: result.getValue('firstname') + ' ' + result.getValue('lastname'),
                    email: result.getValue('email'),
                    employeeId: null, // Field may not exist in all accounts
                    status: status,
                    subsidiary: result.getText('subsidiary'),
                    department: result.getText('department'),
                    lastLogin: result.getValue('lastmodifieddate')
                });
            });
        }

        // Apply offset and limit
        var startIndex = offset % 1000;
        return users.slice(startIndex, startIndex + limit);
    }

    /**
     * Get total count of users matching filters
     * @param {Array} filters - Search filters
     * @returns {Number} Total count
     */
    function getTotalUserCount(filters) {
        var countSearch = search.create({
            type: search.Type.EMPLOYEE,
            filters: filters,
            columns: [
                search.createColumn({
                    name: 'internalid',
                    summary: search.Summary.COUNT
                })
            ]
        });

        var count = 0;
        countSearch.run().each(function(result) {
            count = parseInt(result.getValue({
                name: 'internalid',
                summary: search.Summary.COUNT
            }));
            return false;
        });

        return count;
    }

    /**
     * Get roles assigned to a user
     * @param {String} userId - User entity ID
     * @returns {Array} Roles assigned to user
     */
    function getUserRoles(userId) {
        var roles = [];

        // Validate userId
        if (!userId) {
            log.error('getUserRoles called with invalid userId', userId);
            return roles;
        }

        try {
            // Search for user by entity ID to get their roles
            var roleSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    search.createFilter({
                        name: 'entityid',
                        operator: search.Operator.IS,
                        values: [userId]
                    })
                ],
                columns: [
                    search.createColumn({ name: 'role' })
                ]
            });

            var searchResult = roleSearch.run();
            if (searchResult) {
                searchResult.each(function(result) {
                    try {
                        var roleId = result.getValue('role');
                        var roleName = result.getText('role');

                        if (roleId && roleName) {
                            // Avoid duplicates
                            var exists = false;
                            for (var i = 0; i < roles.length; i++) {
                                if (roles[i].role_id === roleId) {
                                    exists = true;
                                    break;
                                }
                            }

                            if (!exists) {
                                roles.push({
                                    role_id: roleId,
                                    role_name: roleName,
                                    is_custom: roleId.toString().indexOf('customrole') === 0
                                });
                            }
                        }
                    } catch (innerError) {
                        log.error('Error processing role result', innerError.toString());
                    }

                    return true; // Continue iteration
                });
            }

        } catch (e) {
            log.error('Error fetching roles for user', userId + ': ' + e.toString());
        }

        return roles;  // Always return an array, even if empty
    }

    /**
     * Enrich roles with permission details using SuiteQL
     * @param {Array} roles - Array of role objects
     * @returns {Array} Roles with permissions
     */
    function enrichRolesWithPermissions(roles) {
        if (!roles || roles.length === 0) {
            return roles;
        }

        try {
            // Collect all role IDs
            var roleIds = [];
            for (var i = 0; i < roles.length; i++) {
                if (roles[i].role_id) {
                    roleIds.push(roles[i].role_id);
                }
            }

            if (roleIds.length === 0) {
                return roles;
            }

            // Use SuiteQL to fetch permissions for all roles at once
            var sql =
                'SELECT ' +
                '    Role.ID AS role_id, ' +
                '    Role.Name AS role_name, ' +
                '    RolePermissions.PermKey AS permission_key, ' +
                '    RolePermissions.Name AS permission_name, ' +
                '    BUILTIN.DF(RolePermissions.PermLevel) AS permission_level ' +
                'FROM Role ' +
                'INNER JOIN RolePermissions ON (RolePermissions.Role = Role.ID) ' +
                'WHERE Role.ID IN (' + roleIds.join(',') + ') ' +
                'AND Role.IsInactive = \'F\'';

            log.audit('Fetching permissions', 'For ' + roleIds.length + ' roles');

            var queryResults = query.runSuiteQL({
                query: sql
            }).asMappedResults();

            log.audit('Permissions fetched', queryResults.length + ' permissions found');

            // Group permissions by role ID
            var permissionsByRole = {};
            for (var j = 0; j < queryResults.length; j++) {
                var result = queryResults[j];
                var roleId = result.role_id.toString();

                if (!permissionsByRole[roleId]) {
                    permissionsByRole[roleId] = [];
                }

                permissionsByRole[roleId].push({
                    permission: result.permission_key,
                    permission_name: result.permission_name,
                    level: result.permission_level
                });
            }

            // Add permissions to roles
            var enrichedRoles = [];
            for (var k = 0; k < roles.length; k++) {
                var role = roles[k];
                var roleIdStr = role.role_id.toString();
                var permissions = permissionsByRole[roleIdStr] || [];

                enrichedRoles.push({
                    role_id: role.role_id,
                    role_name: role.role_name,
                    is_custom: role.is_custom,
                    permissions: permissions,
                    permission_count: permissions.length
                });
            }

            return enrichedRoles;

        } catch (e) {
            log.error('Error enriching roles with permissions', e.toString());
            // Return roles without permissions if query fails
            return roles;
        }
    }

    return {
        get: doGet,
        post: doPost
    };
});
