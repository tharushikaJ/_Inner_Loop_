BEGIN;

ALTER TABLE projects
    DROP CONSTRAINT IF EXISTS fk_project_intern_pod,
    DROP COLUMN IF EXISTS assigned_intern_pod_id;

ALTER TABLE tasks
    DROP CONSTRAINT IF EXISTS fk_task_intern_pod,
    DROP COLUMN IF EXISTS assigned_intern_pod_id;

DROP TABLE IF EXISTS intern_pod_members CASCADE;
DROP TABLE IF EXISTS intern_pods CASCADE;

COMMIT;
