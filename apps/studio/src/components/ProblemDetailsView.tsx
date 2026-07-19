import { CoreApiError } from "../api/coreClient";

export function ProblemDetailsView({ error }: { error: unknown }) {
  if (error instanceof CoreApiError) {
    const { problem } = error;

    return (
      <div className="problem" role="alert">
        <div className="problem__heading">
          <strong>{problem.title}</strong>
          <span>{problem.status}</span>
        </div>
        {problem.detail ? <p>{problem.detail}</p> : null}
        {problem.errors?.length ? (
          <ul>
            {problem.errors.map((item) => (
              <li key={`${item.pointer}-${item.detail}`}>
                <code>{item.pointer}</code> {item.detail}
              </li>
            ))}
          </ul>
        ) : null}
        <code className="problem__type">{problem.type}</code>
      </div>
    );
  }

  const message =
    error instanceof Error ? error.message : "An unexpected Core error occurred.";

  return (
    <div className="problem" role="alert">
      <div className="problem__heading">
        <strong>Core unavailable</strong>
      </div>
      <p>{message}</p>
    </div>
  );
}
