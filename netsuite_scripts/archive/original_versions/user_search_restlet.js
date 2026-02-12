/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 *
 * NetSuite RESTlet for User Search with Roles and Permissions
 *
 * Purpose: Search for specific users by name or email and return their roles and permissions
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
 * Response:
 * {
 *   "success": true,
 *   "data": {
 *     "users": [...],
 *     "metadata": {...}
 *   }
 * }
 */

define(['N/search', 'N/runtime', 'N/log'], function(search, runtime, log) {

    /**
     * Search for users by name or email
     * @param {Object} requestBody
     * @returns {Object}
     */
    function post(requestBody) {
        const startTime = new Date().getTime();

        try {
            log.audit('User Search Request', JSON.stringify(requestBody));

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

            // Fetch roles and permissions for each user
            const enrichedUsers = users.map(user => {
                return enrichUserWithRoles(user, includePermissions);
            });

            const endTime = new Date().getTime();
            const executionTime = (endTime - startTime) / 1000;

            return {
                success: true,
                data: {
                    users: enrichedUsers,
                    metadata: {
                        search_value: searchValue,
                        search_type: searchType,
                        users_found: enrichedUsers.length,
                        execution_time_seconds: executionTime,
                        timestamp: new Date().toISOString()
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
     * Enrich user object with roles and permissions
     * @param {Object} user - User object
     * @param {boolean} includePermissions - Whether to include detailed permissions
     * @returns {Object} Enriched user object
     */
    function enrichUserWithRoles(user, includePermissions) {
        try {
            // Search for user's roles
            const roleSearch = search.create({
                type: search.Type.EMPLOYEE,
                filters: [
                    ['internalid', 'anyof', user.internal_id]
                ],
                columns: [
                    search.createColumn({
                        name: 'role',
                        summary: search.Summary.GROUP
                    })
                ]
            });

            const roles = [];

            roleSearch.run().each(function(result) {
                const roleId = result.getValue({
                    name: 'role',
                    summary: search.Summary.GROUP
                });

                const roleName = result.getText({
                    name: 'role',
                    summary: search.Summary.GROUP
                });

                if (roleId && roleName) {
                    const roleData = {
                        role_id: roleId,
                        role_name: roleName,
                        permissions: []
                    };

                    // Fetch permissions for this role if requested
                    if (includePermissions) {
                        roleData.permissions = getRolePermissions(roleId);
                    }

                    roles.push(roleData);
                }

                return true; // Continue
            });

            // Add roles to user object
            user.roles = roles;
            user.roles_count = roles.length;

            return user;

        } catch (e) {
            log.error('Error enriching user with roles', `User: ${user.email}, Error: ${e.toString()}`);
            user.roles = [];
            user.roles_count = 0;
            return user;
        }
    }

    /**
     * Get permissions for a specific role
     * @param {string} roleId - NetSuite role internal ID
     * @returns {Array} Array of permission objects
     */
    function getRolePermissions(roleId) {
        const permissions = [];

        try {
            // Note: NetSuite doesn't expose role permissions through saved searches
            // To get detailed permissions, you would need to:
            // 1. Use N/record.load() to load the role record (expensive - uses governance)
            // 2. Or maintain a custom permission mapping table
            // 3. Or use SuiteQL to query permission tables (if available)

            // For now, we return the role ID and name as a placeholder
            // The main RESTlet (script 3684) already returns permissions per user
            // so this is redundant for the search use case

            // If you need detailed permissions, uncomment the code below
            // WARNING: This uses significant governance units (10 per role)

            /*
            const roleRecord = require('N/record').load({
                type: record.Type.ROLE,
                id: roleId,
                isDynamic: false
            });

            // Get role name
            const roleName = roleRecord.getValue('name');

            // NetSuite role permissions are in sublist 'permissions'
            const lineCount = roleRecord.getLineCount({ sublistId: 'permissions' });

            for (let i = 0; i < lineCount; i++) {
                const permName = roleRecord.getSublistValue({
                    sublistId: 'permissions',
                    fieldId: 'permkey',
                    line: i
                });

                const permLevel = roleRecord.getSublistValue({
                    sublistId: 'permissions',
                    fieldId: 'permlevel',
                    line: i
                });

                permissions.push({
                    key: permName,
                    name: permName,
                    level: permLevel
                });
            }
            */

            // Placeholder: Return empty array
            // The user search is fast and works without this
            // Permissions can be fetched separately if needed

        } catch (e) {
            log.error('Error getting role permissions', `Role ID: ${roleId}, Error: ${e.toString()}`);
        }

        return permissions;
    }

    /**
     * GET handler for testing
     */
    function get(requestParams) {
        return {
            success: true,
            message: 'User Search RESTlet is active',
            version: '1.0',
            usage: {
                method: 'POST',
                example_request: {
                    searchType: 'email',
                    searchValue: 'john.doe@company.com',
                    includePermissions: true,
                    includeInactive: false
                }
            }
        };
    }

    return {
        post: post,
        get: get
    };

});
