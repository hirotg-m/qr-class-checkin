import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { del, get, post, put } from "../../api/client";
import type { ClassSummary } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { GRADES } from "../../features/checkin/grades";

type FormState = { name: string; description: string; targetGrades: string[] };

const emptyForm: FormState = { name: "", description: "", targetGrades: [] };

export function ClassListPage() {
  const { auth } = useAuth();
  const token = auth?.token;
  const isAdmin = auth?.role === "admin";

  const [classes, setClasses] = useState<ClassSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadClasses = () => {
    get<ClassSummary[]>("/classes", token)
      .then(setClasses)
      .catch(() => setError("クラス一覧の取得に失敗しました"));
  };

  useEffect(loadClasses, [token]);

  const toggleGrade = (grade: string) => {
    setForm((prev) => ({
      ...prev,
      targetGrades: prev.targetGrades.includes(grade)
        ? prev.targetGrades.filter((g) => g !== grade)
        : [...prev.targetGrades, grade],
    }));
  };

  const startEdit = (cls: ClassSummary) => {
    setEditingId(cls.classId);
    setForm({ name: cls.name, description: cls.description, targetGrades: cls.targetGrades });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm);
  };

  const submitForm = (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const action = editingId
      ? put<ClassSummary>(`/classes/${editingId}`, form, token)
      : post<ClassSummary>("/classes", form, token);
    action
      .then(() => {
        cancelEdit();
        loadClasses();
      })
      .catch(() => setError("保存に失敗しました"))
      .finally(() => setSubmitting(false));
  };

  const deleteClass = (classId: string) => {
    if (!window.confirm("このクラスを削除しますか？")) return;
    del(`/classes/${classId}`, token)
      .then(loadClasses)
      .catch(() => setError("削除に失敗しました"));
  };

  return (
    <div className="page">
      <h1>クラス一覧</h1>

      {error && <p className="error-text">{error}</p>}

      <ul className="stack plain-list">
        {(classes ?? []).map((cls) => (
          <li key={cls.classId} className="card">
            <div className="page-header">
              <div>
                <strong>{cls.name}</strong>
                <p>{cls.description}</p>
                <p>対象学年：{cls.targetGrades.join("、") || "未設定"}</p>
              </div>
              <div className="stack-row">
                <Link className="secondary-button" to={`/dashboard/classes/${cls.classId}/schedule`}>
                  活動予定
                </Link>
                <Link className="secondary-button" to={`/dashboard/classes/${cls.classId}/stats`}>
                  統計
                </Link>
                <Link className="secondary-button" to={`/dashboard/classes/${cls.classId}/participants`}>
                  参加者名簿
                </Link>
                <Link className="secondary-button" to={`/dashboard/classes/${cls.classId}/qr`}>
                  QRコード
                </Link>
                {isAdmin && (
                  <>
                    <Link className="secondary-button" to={`/dashboard/classes/${cls.classId}/pin`}>
                      PIN管理
                    </Link>
                    <button type="button" className="secondary-button" onClick={() => startEdit(cls)}>
                      編集
                    </button>
                    <button type="button" className="link-button" onClick={() => deleteClass(cls.classId)}>
                      削除
                    </button>
                  </>
                )}
              </div>
            </div>
          </li>
        ))}
        {classes && classes.length === 0 && <li>まだクラスが登録されていません</li>}
      </ul>

      {isAdmin && (
        <form className="stack card" onSubmit={submitForm}>
          <h2>{editingId ? "クラスを編集" : "クラスを追加"}</h2>
          <label className="field">
            <span>クラス名</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label className="field">
            <span>説明</span>
            <input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          </label>
          <fieldset className="field">
            <legend>対象学年</legend>
            <div className="grade-grid">
              {GRADES.map((grade) => (
                <label key={grade} className="checkbox-field">
                  <input type="checkbox" checked={form.targetGrades.includes(grade)} onChange={() => toggleGrade(grade)} />
                  {grade}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="stack-row">
            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? "保存中…" : editingId ? "更新" : "追加"}
            </button>
            {editingId && (
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
