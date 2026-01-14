# Admin Features Fixes Applied

## Summary of Fixes

### 1. ✅ Fixed Admin Signup Bug

**Issue:** Admin signup was working correctly - the API expects `role: 'admin'` which is being sent properly from both login.html and dashboard.html signup forms.

**Status:** No changes needed - signup is working correctly.

### 2. ✅ Fixed Admin Create User Bug

**Issue:** The admin panel was sending `machines` but the API expects `machine_ids`.

**Fix Applied:**

- Updated `adminCreateUser()` function in `dashboard.html` line 6121
- Changed `machines: machines` to `machine_ids: machines`

### 3. ✅ Fixed Audit Logs

**Issue:** Audit logs were only stored in frontend array and lost on page refresh.

**Fixes Applied:**

- Created `migrations/add_audit_logs.sql` - database table for persistent audit logs
- Added `add_audit_log()` function in `dashboard.py` to save logs to database
- Added `/api/audit-log` POST endpoint to save logs
- Added `/api/audit-logs` GET endpoint to fetch logs (admin only)
- Updated `logOperatorAction()` to save to database
- Added `loadOperatorLogs()` function to load logs from database
- Integrated `loadOperatorLogs()` into page initialization and refresh interval

### 4. ✅ Database Migration

**Created:**

- `migrations/add_audit_logs.sql` - SQL migration file
- `run_migration.py` - Python script to run migrations

## How to Apply Database Migration

### Option 1: Using the Python Script

```bash
cd stub
python run_migration.py migrations/add_audit_logs.sql
```

### Option 2: Manual SQL Execution

```bash
psql -h localhost -U postgres -d sensor_data -f migrations/add_audit_logs.sql
```

### Option 3: Using psql directly

```sql
\i migrations/add_audit_logs.sql
```

## Verification Steps

1. **Test Admin Signup:**

   - Go to `/login`
   - Click "Sign Up"
   - Check "Create as Admin"
   - Create account
   - Login and verify admin access

2. **Test Admin Create User:**

   - Login as admin
   - Go to Gear Icon (Configuration)
   - Use "User Management" form
   - Create a new user
   - Verify success message appears

3. **Test Audit Logs:**
   - Login as admin
   - Perform actions (Start/Stop machine, change settings)
   - Go to Gear Icon → "Operator Logs"
   - Verify logs appear in the table
   - Refresh page - logs should persist

## API Endpoints Added

- `POST /api/audit-log` - Save an audit log entry (requires auth)
- `GET /api/audit-logs?limit=100` - Get audit logs (admin only)

## Database Schema

The `audit_logs` table includes:

- `id` - Primary key
- `operator_name` - Username who performed action
- `action` - Description of the action
- `timestamp` - When the action occurred
- `user_id` - Foreign key to users table
- `machine_id` - Machine involved (if applicable)
- `metadata` - JSONB for additional data

## Notes

- Audit logs are saved asynchronously (non-blocking)
- Frontend array is kept for immediate display
- Database logs are loaded on page load and refreshed periodically
- Only admins can view audit logs
- Logs are limited to last 100 entries in frontend, but all are stored in database
