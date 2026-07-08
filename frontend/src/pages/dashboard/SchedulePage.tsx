import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { del, get, post, put } from "../../api/client";
import type { ClassSummary, ScheduleEntry } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { currentMonth, formatDateWithWeekday } from "../../lib/date";

type FormState = { date: string; startTime: string; endTime: string; location: string };

const emptyForm: FormState = { date: "", startTime: "", endTime: "", location: "" };

export function SchedulePage() {
  const { classId = "" } = useParams<{ classId: string }>();
  const { auth } = useAuth();
  const token = auth?.token;
  const isAdmin = auth?.role === "admin";

  const [classInfo, setClassInfo] = useState<ClassSummary | null>(null);
  const [month, setMonth] = useState(currentMonth());
  const [entries, setEntries] = useState<ScheduleEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingDate, setEditingDate] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    get<ScheduleEntry[]>(`/classes/${classId}/schedule?month=${month}`, token)
      .then(setEntries)
      .catch(() => setError("活動予定の取得に失敗しました"));
  };

  useEffect(load, [classId, month, token]);

  useEffect(() => {
    get<ClassSummary[]>("/classes", token)
      .then((list) => setClassInfo(list.find((c) => c.classId === classId) ?? null))
      .catch(() => undefined);
  }, [classId, token]);

  const startEdit = (entry: ScheduleEntry) => {
    setEditingDate(entry.date);
    setForm({ date: entry.date, startTime: entry.startTime, endTime: entry.endTime, location: entry.location });
  };

  const cancelEdit = () => {
    setEditingDate(null);
    setForm(emptyForm);
  };

  const submitForm = (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const action = editingDate
      ? put<ScheduleEntry>(`/classes/${classId}/schedule/${editingDate}`, form, token)
      : post<ScheduleEntry>(`/classes/${classId}/schedule`, form, token);
    action
      .then(() => {
        cancelEdit();
        load();
      })
      .catch(() => setError("保存に失敗しました（同じ日付が既に登録されている可能性があります）"))
      .finally(() => setSubmitting(false));
  };

  const deleteEntry = (date: string) => {
    if (!window.confirm("この活動予定を削除しますか？")) return;
    del(`/classes/${classId}/schedule/${date}`, token)
      .then(load)
      .catch(() => setError("削除に失敗しました"));
  };

  return (
    <div className="page page-wide">
      <h1>{classInfo ? `${classInfo.name} 活動予定` : "活動予定"}</h1>
      <label className="field">
        <span>月</span>
        <input type="month" value={month} onChange={(event) => setMonth(event.target.value)} />
      </label>

      {error && <p className="error-text">{error}</p>}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>日付</th>
              <th>時間</th>
              <th>会場</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {(entries ?? []).map((entry) => (
              <tr key={entry.date}>
                <td>{formatDateWithWeekday(entry.date)}</td>
                <td>
                  {entry.startTime} 〜 {entry.endTime}
                </td>
                <td>{entry.location || "会場未設定"}</td>
                <td className="stack-row">
                  <Link className="secondary-button" to={`/dashboard/classes/${classId}/sessions/${entry.date}`}>
                    参加者一覧
                  </Link>
                  {isAdmin && (
                    <>
                      <button type="button" className="secondary-button" onClick={() => startEdit(entry)}>
                        編集
                      </button>
                      <button type="button" className="link-button" onClick={() => deleteEntry(entry.date)}>
                        削除
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {entries && entries.length === 0 && <p>この月の活動予定はまだありません</p>}
      </div>

      {isAdmin && (
        <form className="stack card" onSubmit={submitForm}>
          <h2>{editingDate ? `${formatDateWithWeekday(editingDate)}を編集` : "活動予定を追加"}</h2>
          {!editingDate && (
            <label className="field">
              <span>日付</span>
              <input
                type="date"
                value={form.date}
                onChange={(event) => setForm({ ...form, date: event.target.value })}
                required
              />
            </label>
          )}
          <label className="field">
            <span>開始時刻</span>
            <input
              type="time"
              value={form.startTime}
              onChange={(event) => setForm({ ...form, startTime: event.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>終了時刻</span>
            <input
              type="time"
              value={form.endTime}
              onChange={(event) => setForm({ ...form, endTime: event.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>会場</span>
            <input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} />
          </label>
          <div className="stack-row">
            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? "保存中…" : editingDate ? "更新" : "追加"}
            </button>
            {editingDate && (
              <button type="button" className="secondary-button" onClick={cancelEdit}>
                キャンセル
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
