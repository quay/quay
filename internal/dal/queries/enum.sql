-- name: GetMediaTypeByName :one
SELECT id FROM mediatype WHERE name = ?;

-- name: GetVisibilityByName :one
SELECT id FROM visibility WHERE name = ?;

-- name: GetRepositoryKindByName :one
SELECT id FROM repositorykind WHERE name = ?;

-- name: GetTagKindByName :one
SELECT id FROM tagkind WHERE name = ?;

-- name: GetAlembicVersion :one
SELECT version_num FROM alembic_version LIMIT 1;
