DELETE FROM "RolePermission"
WHERE "role" = 'viewer'
  AND "permission" = 'config.write';
