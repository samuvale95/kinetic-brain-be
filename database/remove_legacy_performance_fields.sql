-- Remove legacy performance fields (run manually if Alembic lacks privileges)

ALTER TABLE performance_metrics DROP COLUMN IF EXISTS metric_type;
ALTER TABLE performance_metrics DROP COLUMN IF EXISTS threshold_value;
ALTER TABLE performance_metrics DROP COLUMN IF EXISTS max_value;
ALTER TABLE performance_metrics DROP COLUMN IF EXISTS rest_value;
ALTER TABLE performance_metrics DROP COLUMN IF EXISTS zones_json;


