import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

export function BackupPanel() {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [confirmRestoreId, setConfirmRestoreId] = useState<string | null>(null);

  const backupsQuery = useQuery({
    queryKey: queryKeys.backups,
    queryFn: () => client.listBackups(),
    refetchInterval: 15_000,
  });

  const createBackup = useMutation({
    mutationFn: () => client.createBackup({}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.backups });
    },
  });

  const restoreBackup = useMutation({
    mutationFn: (backupId: string) => client.restoreBackup(backupId),
    onSuccess: () => {
      setConfirmRestoreId(null);
    },
  });

  return (
    <Panel
      eyebrow="System"
      title="Backups"
      toolbar={
        <button
          className="button button--primary"
          type="button"
          onClick={() => createBackup.mutate()}
          disabled={createBackup.isPending}
        >
          {createBackup.isPending ? "Creating backup…" : "Create backup"}
        </button>
      }
    >
      {createBackup.isPending ? (
        <div className="backup-running" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Creating database backup via SQLite Backup API…</span>
        </div>
      ) : null}
      {createBackup.isError ? (
        <ProblemDetailsView error={createBackup.error} />
      ) : null}
      {createBackup.isSuccess ? (
        <div className="backup-created">
          Backup created ({(createBackup.data.fileSizeBytes / 1024).toFixed(1)} KB)
        </div>
      ) : null}

      {backupsQuery.isPending ? (
        <LoadingState>Loading backups…</LoadingState>
      ) : null}
      {backupsQuery.isError ? (
        <ProblemDetailsView error={backupsQuery.error} />
      ) : null}
      {backupsQuery.isSuccess && backupsQuery.data.items.length === 0 ? (
        <EmptyState>No backups yet. Create your first database backup.</EmptyState>
      ) : null}
      {backupsQuery.isSuccess && backupsQuery.data.items.length > 0 ? (
        <div className="backup-list">
          {backupsQuery.data.items.map((backup) => (
            <div key={backup.id} className="backup-item">
              <div className="backup-item__header">
                <span
                  className={`badge ${backup.status === "completed" ? "badge--clean" : "badge--error"}`}
                >
                  {backup.status}
                </span>
                {backup.label ? <strong>{backup.label}</strong> : null}
                <span className="backup-item__size">
                  {(backup.fileSizeBytes / 1024).toFixed(1)} KB
                </span>
              </div>
              <div className="backup-item__meta">
                <span>{formatTimestamp(backup.createdAt)}</span>
                {backup.dbVersion ? (
                  <span>DB: {backup.dbVersion.slice(0, 8)}</span>
                ) : null}
              </div>

              {confirmRestoreId === backup.id ? (
                <div className="backup-item__confirm">
                  <p className="backup-item__warning">
                    Restoring will replace the entire Core artifact database and
                    requires restarting Core afterward. All current data will be
                    replaced.
                  </p>
                  <div className="backup-item__actions">
                    <button
                      className="button"
                      type="button"
                      onClick={() => setConfirmRestoreId(null)}
                      disabled={restoreBackup.isPending}
                    >
                      Cancel
                    </button>
                    <button
                      className="button button--error"
                      type="button"
                      onClick={() => restoreBackup.mutate(backup.id)}
                      disabled={restoreBackup.isPending}
                    >
                      {restoreBackup.isPending
                        ? "Restoring…"
                        : "Confirm restore"}
                    </button>
                  </div>
                </div>
              ) : backup.status === "completed" ? (
                <button
                  className="button button--danger"
                  type="button"
                  onClick={() => setConfirmRestoreId(backup.id)}
                >
                  Restore
                </button>
              ) : null}

              {backup.errorMessage ? (
                <div className="backup-item__error">{backup.errorMessage}</div>
              ) : null}
            </div>
          ))}

          {restoreBackup.isSuccess ? (
            <div className="backup-restore-success">
              {restoreBackup.data.message}
            </div>
          ) : null}
          {restoreBackup.isError ? (
            <ProblemDetailsView error={restoreBackup.error} />
          ) : null}
        </div>
      ) : null}
    </Panel>
  );
}
