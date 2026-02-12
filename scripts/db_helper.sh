#!/bin/bash

# Database Helper Script - Common database operations for local development

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

DB_CONTAINER="compliance-postgres"
DB_NAME="compliance_db"
DB_USER="compliance_user"

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if container is running
if ! docker ps | grep -q $DB_CONTAINER; then
    echo -e "${YELLOW}⚠ Database container is not running${NC}"
    echo "Start it with: docker-compose up -d postgres"
    exit 1
fi

# Show menu
show_menu() {
    print_header "Database Helper - Local Development"
    echo "1. Connect to database (psql)"
    echo "2. View all SOD rules"
    echo "3. View database schema"
    echo "4. View recent violations"
    echo "5. View user statistics"
    echo "6. Reset database (drop all data)"
    echo "7. Reload schema"
    echo "8. Backup database"
    echo "9. Run custom query"
    echo "0. Exit"
    echo ""
}

# Connect to database
connect_db() {
    print_info "Connecting to database..."
    docker exec -it $DB_CONTAINER psql -U $DB_USER -d $DB_NAME
}

# View all SOD rules
view_rules() {
    print_header "SOD Rules"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT
            rule_id,
            rule_name,
            rule_type,
            severity,
            regulatory_framework,
            is_active
        FROM sod_rules
        ORDER BY severity DESC, rule_id;
    "
}

# View schema
view_schema() {
    print_header "Database Schema"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT
            table_name,
            (SELECT COUNT(*) FROM information_schema.columns
             WHERE table_schema = 'public' AND columns.table_name = tables.table_name) as columns
        FROM information_schema.tables tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    "
}

# View recent violations
view_violations() {
    print_header "Recent Violations (Last 10)"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT
            violation_id,
            user_id,
            severity,
            status,
            detected_at::date as detected
        FROM violations
        ORDER BY detected_at DESC
        LIMIT 10;
    "
}

# View user statistics
view_users() {
    print_header "User Statistics"
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT
            status,
            COUNT(*) as user_count
        FROM users
        GROUP BY status;
    "
    echo ""
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        SELECT
            u.user_id,
            u.name,
            COUNT(DISTINCT ur.role_id) as role_count,
            COUNT(v.violation_id) as violation_count
        FROM users u
        LEFT JOIN user_roles ur ON u.user_id = ur.user_id
        LEFT JOIN violations v ON u.user_id = v.user_id AND v.status = 'OPEN'
        WHERE u.status = 'ACTIVE'
        GROUP BY u.user_id, u.name
        HAVING COUNT(v.violation_id) > 0
        ORDER BY violation_count DESC
        LIMIT 5;
    "
}

# Reset database
reset_db() {
    print_header "Reset Database"
    echo -e "${YELLOW}⚠ WARNING: This will delete ALL data!${NC}"
    read -p "Are you sure? Type 'yes' to confirm: " confirmation
    if [ "$confirmation" != "yes" ]; then
        print_info "Cancelled"
        return
    fi

    print_info "Dropping all tables..."
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
        DROP SCHEMA public CASCADE;
        CREATE SCHEMA public;
        GRANT ALL ON SCHEMA public TO $DB_USER;
        GRANT ALL ON SCHEMA public TO public;
    "
    print_success "Database reset complete"
    print_info "Reload schema with option 7"
}

# Reload schema
reload_schema() {
    print_header "Reload Schema"
    print_info "Applying database schema..."
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME < database/schema.sql 2>&1 | grep -v "NOTICE" || true
    print_success "Schema reloaded"
}

# Backup database
backup_db() {
    print_header "Backup Database"
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    print_info "Creating backup: $BACKUP_FILE"
    docker exec $DB_CONTAINER pg_dump -U $DB_USER -d $DB_NAME > "$BACKUP_FILE"
    print_success "Backup saved to $BACKUP_FILE"
}

# Run custom query
custom_query() {
    print_header "Custom Query"
    echo "Enter your SQL query (end with semicolon):"
    read -e query
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "$query"
}

# Main loop
while true; do
    show_menu
    read -p "Select option: " choice

    case $choice in
        1) connect_db ;;
        2) view_rules ;;
        3) view_schema ;;
        4) view_violations ;;
        5) view_users ;;
        6) reset_db ;;
        7) reload_schema ;;
        8) backup_db ;;
        9) custom_query ;;
        0) echo "Goodbye!"; exit 0 ;;
        *) echo "Invalid option" ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
