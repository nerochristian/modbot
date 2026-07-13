-- CreateTable
CREATE TABLE "Guild" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "icon" TEXT,
    "installed" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "GuildMembership" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'viewer',
    "status" TEXT NOT NULL DEFAULT 'active',
    "source" TEXT NOT NULL DEFAULT 'discord',
    "verifiedAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "GuildMembership_guildId_fkey" FOREIGN KEY ("guildId") REFERENCES "Guild" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "GuildMembership_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_ActivityLog" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT,
    "actorName" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "target" TEXT,
    "metadata" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ActivityLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_ActivityLog" ("action", "actorName", "createdAt", "id", "metadata", "target", "userId") SELECT "action", "actorName", "createdAt", "id", "metadata", "target", "userId" FROM "ActivityLog";
DROP TABLE "ActivityLog";
ALTER TABLE "new_ActivityLog" RENAME TO "ActivityLog";
CREATE INDEX "ActivityLog_guildId_createdAt_idx" ON "ActivityLog"("guildId", "createdAt");
CREATE TABLE "new_AuditLog" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT,
    "actorName" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entity" TEXT NOT NULL,
    "entityId" TEXT,
    "ip" TEXT,
    "userAgent" TEXT,
    "metadata" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "AuditLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_AuditLog" ("action", "actorName", "createdAt", "entity", "entityId", "id", "ip", "metadata", "userAgent", "userId") SELECT "action", "actorName", "createdAt", "entity", "entityId", "id", "ip", "metadata", "userAgent", "userId" FROM "AuditLog";
DROP TABLE "AuditLog";
ALTER TABLE "new_AuditLog" RENAME TO "AuditLog";
CREATE INDEX "AuditLog_guildId_createdAt_idx" ON "AuditLog"("guildId", "createdAt");
CREATE INDEX "AuditLog_guildId_entity_idx" ON "AuditLog"("guildId", "entity");
CREATE TABLE "new_Invoice" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT NOT NULL,
    "number" TEXT NOT NULL,
    "amount" INTEGER NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'paid',
    "issuedAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "periodStart" DATETIME NOT NULL,
    "periodEnd" DATETIME NOT NULL,
    CONSTRAINT "Invoice_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_Invoice" ("amount", "id", "issuedAt", "number", "periodEnd", "periodStart", "status", "userId") SELECT "amount", "id", "issuedAt", "number", "periodEnd", "periodStart", "status", "userId" FROM "Invoice";
DROP TABLE "Invoice";
ALTER TABLE "new_Invoice" RENAME TO "Invoice";
CREATE UNIQUE INDEX "Invoice_number_key" ON "Invoice"("number");
CREATE INDEX "Invoice_guildId_userId_idx" ON "Invoice"("guildId", "userId");
CREATE TABLE "new_Notification" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT NOT NULL,
    "type" TEXT NOT NULL DEFAULT 'system',
    "level" TEXT NOT NULL DEFAULT 'info',
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "read" BOOLEAN NOT NULL DEFAULT false,
    "href" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Notification_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_Notification" ("body", "createdAt", "href", "id", "level", "read", "title", "type", "userId") SELECT "body", "createdAt", "href", "id", "level", "read", "title", "type", "userId" FROM "Notification";
DROP TABLE "Notification";
ALTER TABLE "new_Notification" RENAME TO "Notification";
CREATE INDEX "Notification_guildId_userId_idx" ON "Notification"("guildId", "userId");
CREATE INDEX "Notification_guildId_userId_read_idx" ON "Notification"("guildId", "userId", "read");
CREATE TABLE "new_Report" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL DEFAULT 'revenue',
    "status" TEXT NOT NULL DEFAULT 'ready',
    "format" TEXT NOT NULL DEFAULT 'csv',
    "params" TEXT,
    "createdById" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Report_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "User" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_Report" ("createdAt", "createdById", "format", "id", "name", "params", "status", "type") SELECT "createdAt", "createdById", "format", "id", "name", "params", "status", "type" FROM "Report";
DROP TABLE "Report";
ALTER TABLE "new_Report" RENAME TO "Report";
CREATE INDEX "Report_guildId_createdAt_idx" ON "Report"("guildId", "createdAt");
CREATE TABLE "new_RolePermission" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "role" TEXT NOT NULL,
    "permission" TEXT NOT NULL,
    "allowed" BOOLEAN NOT NULL DEFAULT true
);
INSERT INTO "new_RolePermission" ("allowed", "id", "permission", "role") SELECT "allowed", "id", "permission", "role" FROM "RolePermission";
DROP TABLE "RolePermission";
ALTER TABLE "new_RolePermission" RENAME TO "RolePermission";
CREATE INDEX "RolePermission_guildId_role_idx" ON "RolePermission"("guildId", "role");
CREATE UNIQUE INDEX "RolePermission_guildId_role_permission_key" ON "RolePermission"("guildId", "role", "permission");
CREATE TABLE "new_SavedView" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "page" TEXT NOT NULL,
    "state" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "SavedView_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_SavedView" ("createdAt", "id", "name", "page", "state", "userId") SELECT "createdAt", "id", "name", "page", "state", "userId" FROM "SavedView";
DROP TABLE "SavedView";
ALTER TABLE "new_SavedView" RENAME TO "SavedView";
CREATE INDEX "SavedView_guildId_userId_idx" ON "SavedView"("guildId", "userId");
CREATE TABLE "new_Subscription" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "guildId" TEXT NOT NULL DEFAULT '',
    "userId" TEXT NOT NULL,
    "plan" TEXT NOT NULL DEFAULT 'pro',
    "status" TEXT NOT NULL DEFAULT 'active',
    "seats" INTEGER NOT NULL DEFAULT 1,
    "interval" TEXT NOT NULL DEFAULT 'month',
    "amount" INTEGER NOT NULL DEFAULT 4900,
    "currentPeriodEnd" DATETIME NOT NULL,
    "cancelAtPeriodEnd" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Subscription_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_Subscription" ("amount", "cancelAtPeriodEnd", "createdAt", "currentPeriodEnd", "id", "interval", "plan", "seats", "status", "userId") SELECT "amount", "cancelAtPeriodEnd", "createdAt", "currentPeriodEnd", "id", "interval", "plan", "seats", "status", "userId" FROM "Subscription";
DROP TABLE "Subscription";
ALTER TABLE "new_Subscription" RENAME TO "Subscription";
CREATE INDEX "Subscription_guildId_idx" ON "Subscription"("guildId");
CREATE UNIQUE INDEX "Subscription_guildId_userId_key" ON "Subscription"("guildId", "userId");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE INDEX "GuildMembership_userId_status_idx" ON "GuildMembership"("userId", "status");

-- CreateIndex
CREATE INDEX "GuildMembership_guildId_role_status_idx" ON "GuildMembership"("guildId", "role", "status");

-- CreateIndex
CREATE UNIQUE INDEX "GuildMembership_guildId_userId_key" ON "GuildMembership"("guildId", "userId");
