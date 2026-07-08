import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { get } from "../../api/client";
import type { StatsEntry } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { GRADES } from "../../features/checkin/grades";

const COLORS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#84cc16"];

function toDateInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function defaultRange(): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setMonth(from.getMonth() - 3);
  return { from: toDateInput(from), to: toDateInput(to) };
}

export function StatsPage() {
  const { classId = "" } = useParams<{ classId: string }>();
  const { auth } = useAuth();
  const token = auth?.token;

  const [range, setRange] = useState(defaultRange());
  const [entries, setEntries] = useState<StatsEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    get<StatsEntry[]>(`/classes/${classId}/stats/participants?from=${range.from}&to=${range.to}`, token)
      .then(setEntries)
      .catch(() => setError("統計の取得に失敗しました"));
  }, [classId, range, token]);

  const chartData = (entries ?? []).map((entry) => ({ date: entry.date, ...entry.byGrade }));

  return (
    <div className="page">
      <h1>参加人数推移</h1>

      <div className="stack-row">
        <label className="field">
          <span>開始日</span>
          <input type="date" value={range.from} onChange={(event) => setRange({ ...range, from: event.target.value })} />
        </label>
        <label className="field">
          <span>終了日</span>
          <input type="date" value={range.to} onChange={(event) => setRange({ ...range, to: event.target.value })} />
        </label>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div style={{ width: "100%", height: 360 }}>
        <ResponsiveContainer>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            {GRADES.map((grade, index) => (
              <Bar key={grade} dataKey={grade} stackId="grade" fill={COLORS[index % COLORS.length]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
