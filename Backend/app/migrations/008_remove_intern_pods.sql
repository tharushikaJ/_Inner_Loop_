BEGIN;

-- This migration only removes the retired Intern Pods objects.  Do not use
-- CASCADE when dropping the tables: an unexpected dependency should fail the
-- migration instead of deleting unrelated application data.
ALTER TABLE IF EXISTS projects
    DROP CONSTRAINT IF EXISTS fk_project_intern_pod,
    DROP COLUMN IF EXISTS assigned_intern_pod_id;

ALTER TABLE IF EXISTS tasks
    DROP CONSTRAINT IF EXISTS fk_task_intern_pod,
    DROP COLUMN IF EXISTS assigned_intern_pod_id;

DROP TABLE IF EXISTS intern_pod_members;
DROP TABLE IF EXISTS intern_pods;

COMMIT;
