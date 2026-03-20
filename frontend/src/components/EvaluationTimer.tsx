import { useEffect, useMemo, useState } from "react";

export function formatDurationSeconds(totalSeconds: number | null | undefined): string {
  const safeSeconds = Math.max(0, totalSeconds ?? 0);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function EvaluationTimer({
  initialSeconds = 0,
  onChange,
}: {
  initialSeconds?: number;
  onChange?: (seconds: number) => void;
}) {
  const [elapsedSeconds, setElapsedSeconds] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    // only reset when the timer is not actively running, to avoid a feedback loop
    // where onChange updates parent state and parent re-feeds initialSeconds every second.
    if (!isRunning) {
      setElapsedSeconds(initialSeconds);
    }
  }, [initialSeconds, isRunning]);

  useEffect(() => {
    if (!isRunning) return;
    const timerId = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(timerId);
  }, [isRunning]);

  useEffect(() => {
    onChange?.(elapsedSeconds);
  }, [elapsedSeconds, onChange]);

  const displayValue = useMemo(() => formatDurationSeconds(elapsedSeconds), [elapsedSeconds]);

  return (
    <div
      style={{
        border: "1px solid #bfdbfe",
        borderRadius: 14,
        padding: 16,
        background: "#f8fbff",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, color: "#4b5563", marginBottom: 6 }}>Elapsed Time</div>
          <div style={{ fontSize: 30, fontWeight: 800, color: "#023e8a", letterSpacing: "0.04em" }}>{displayValue}</div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" onClick={() => setIsRunning(true)} disabled={isRunning}>
            Start
          </button>
          <button type="button" onClick={() => setIsRunning(false)} disabled={!isRunning}>
            Pause
          </button>
          <button
            type="button"
            onClick={() => {
              setIsRunning(false);
              setElapsedSeconds(0);
            }}
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
