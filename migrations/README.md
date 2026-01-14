# Database Migrations

## Sensor Metadata Migration

This migration adds the `sensor_metadata` table to enrich sensor data with location, equipment, and criticality information.

### Running the Migration

1. **Using Docker (Recommended)**:
   ```bash
   docker exec -i stub-postgres psql -U sensoruser -d sensordb < migrations/add_sensor_metadata.sql
   ```

2. **Using psql directly**:
   ```bash
   psql -U sensoruser -d sensordb -f migrations/add_sensor_metadata.sql
   ```

### What the Migration Does

- Creates `sensor_metadata` table with columns:
  - `sensor_name` (PRIMARY KEY)
  - `machine_type`
  - `category`
  - `location`
  - `equipment_section`
  - `criticality` (low/medium/high/critical)
  - `unit`
  
- Seeds the table with metadata for all 50 existing sensors

- Creates indexes for efficient queries

### Verification

After running the migration, verify it worked:

```sql
SELECT COUNT(*) FROM sensor_metadata;  -- Should return 50
SELECT * FROM sensor_metadata LIMIT 5;  -- View sample data
```

### Backward Compatibility

- The migration uses `CREATE TABLE IF NOT EXISTS` - safe to run multiple times
- Uses `ON CONFLICT DO NOTHING` for inserts - safe to re-run
- The backend service gracefully falls back if metadata is unavailable
- Existing dashboards continue to work without metadata

