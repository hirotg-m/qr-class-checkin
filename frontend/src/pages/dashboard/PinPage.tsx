import { type FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { extractMessage, get, put } from "../../api/client";
import type { MonthlyPin } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { currentMonth } from "../../lib/date";

export function PinPage() {
  const { classId = "" } = useParams<{ classId: string }>();
  const { auth } = useAuth();
  const token = auth?.token;
  const isAdmin = auth?.role === "admin";

  const [month, setMonth] = useState(currentMonth());
  const [currentPin, setCurrentPin] = useState<MonthlyPin | null>(null);
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [savedMonth, setSavedMonth] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    get<MonthlyPin>(`/classes/${classId}/pin/${month}`, token)
      .then(setCurrentPin)
      .catch(() => setCurrentPin(null));
  }, [classId, month, token]);

  const submitForm = (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSavedMonth(null);
    put(`/classes/${classId}/pin/${month}`, { pin }, token)
      .then(() => {
        setSavedMonth(month);
        setCurrentPin({ classId, month, pin });
        setPin("");
      })
      .catch((err: unknown) => setError(extractMessage(err, "PINの保存に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  if (!isAdmin) {
    return (
      <div className="page">
        <h1>月次PIN管理</h1>
        <p>この機能は管理者のみ利用できます。</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>月次PIN管理</h1>
      <p>保護者の登録画面で入力してもらう暗証番号を月ごとに設定します。</p>

      {error && <p className="error-text">{error}</p>}
      {savedMonth && !error && <p>{savedMonth}のPINを保存しました。</p>}

      <form className="stack card" onSubmit={submitForm}>
        <label className="field">
          <span>対象月</span>
          <input type="month" value={month} onChange={(event) => setMonth(event.target.value)} required />
        </label>
        <p>現在のPIN：{currentPin?.pin ?? "未設定"}</p>
        <label className="field">
          <span>新しいPIN</span>
          <input
            type="text"
            inputMode="numeric"
            value={pin}
            onChange={(event) => setPin(event.target.value)}
            placeholder="例：1234"
            required
          />
        </label>
        <button type="submit" className="primary-button" disabled={submitting || pin.length === 0}>
          {submitting ? "保存中…" : "保存"}
        </button>
      </form>
    </div>
  );
}
