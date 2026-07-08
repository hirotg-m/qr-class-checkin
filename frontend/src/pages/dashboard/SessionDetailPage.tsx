import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { del, extractMessage, get, post, put } from "../../api/client";
import type {
  CheckinResultItem,
  ChildRow,
  ClassSummary,
  ConfirmationPayload,
  ParticipantView,
  SessionDetail,
} from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { ChildrenForm } from "../../features/checkin/ChildrenForm";
import { CheckinReview } from "../../features/checkin/CheckinReview";
import { GRADES } from "../../features/checkin/grades";
import { formatDateWithWeekday } from "../../lib/date";

type ProxyStep = { name: "idle" } | { name: "form" } | { name: "review"; childRows: ChildRow[]; items: CheckinResultItem[] };
type EditForm = { name: string; grade: string };

export function SessionDetailPage() {
  const { classId = "", date = "" } = useParams<{ classId: string; date: string }>();
  const { auth } = useAuth();
  const token = auth?.token;
  const isAdmin = auth?.role === "admin";

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [classInfo, setClassInfo] = useState<ClassSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [proxyStep, setProxyStep] = useState<ProxyStep>({ name: "idle" });
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ name: "", grade: "" });

  const loadSession = () => {
    get<SessionDetail>(`/classes/${classId}/sessions/${date}`, token)
      .then(setSession)
      .catch(() => setError("参加者一覧の取得に失敗しました"));
  };

  useEffect(loadSession, [classId, date, token]);

  useEffect(() => {
    get<ClassSummary[]>("/classes", token)
      .then((list) => setClassInfo(list.find((c) => c.classId === classId) ?? null))
      .catch(() => undefined);
  }, [classId, token]);

  const submitProxyChildren = (childRows: ChildRow[]) => {
    setSubmitting(true);
    setError(null);
    post<{ results: CheckinResultItem[] }>(`/classes/${classId}/sessions/${date}/proxy`, { children: childRows }, token)
      .then((res) => setProxyStep({ name: "review", childRows, items: res.results }))
      .catch((err: unknown) => setError(extractMessage(err, "参加者の照合に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  const submitProxyConfirmations = (confirmations: ConfirmationPayload[]) => {
    setSubmitting(true);
    setError(null);
    post(`/classes/${classId}/sessions/${date}/proxy/confirm`, { confirmations }, token)
      .then(() => {
        setProxyStep({ name: "idle" });
        loadSession();
      })
      .catch((err: unknown) => setError(extractMessage(err, "代理入力の登録に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  const startEdit = (participant: ParticipantView) => {
    setEditingId(participant.participantId);
    setEditForm({ name: participant.name, grade: participant.grade });
  };

  const cancelEdit = () => setEditingId(null);

  const submitEdit = (participantId: string) => {
    setSubmitting(true);
    setError(null);
    put(`/classes/${classId}/participants/${participantId}`, editForm, token)
      .then(() => {
        setEditingId(null);
        loadSession();
      })
      .catch((err: unknown) => setError(extractMessage(err, "参加者情報の修正に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  const deleteParticipant = (participantId: string) => {
    if (!window.confirm("この来場記録を削除しますか？（参加者名簿からは削除されません）")) return;
    setSubmitting(true);
    setError(null);
    del(`/classes/${classId}/sessions/${date}/participants/${participantId}`, token)
      .then(loadSession)
      .catch((err: unknown) => setError(extractMessage(err, "来場記録の削除に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="page page-wide">
      <h1>{formatDateWithWeekday(date)}の参加者</h1>
      {error && <p className="error-text">{error}</p>}

      {session?.schedule && (
        <p>
          {session.schedule.startTime} 〜 {session.schedule.endTime}（{session.schedule.location || "会場未設定"}）
        </p>
      )}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>学年</th>
              <th>氏名</th>
              <th>状態</th>
              <th>参加回数</th>
              <th>前回参加日</th>
              {isAdmin && <th>入力</th>}
              {isAdmin && <th>時刻</th>}
              {isAdmin && <th>操作</th>}
            </tr>
          </thead>
          <tbody>
            {(session?.participants ?? []).map((participant) =>
              editingId === participant.participantId ? (
                <tr key={participant.participantId}>
                  <td>
                    <select
                      value={editForm.grade}
                      onChange={(event) => setEditForm({ ...editForm, grade: event.target.value })}
                    >
                      {(classInfo?.targetGrades ?? GRADES).map((grade) => (
                        <option key={grade} value={grade}>
                          {grade}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      value={editForm.name}
                      onChange={(event) => setEditForm({ ...editForm, name: event.target.value })}
                    />
                  </td>
                  <td colSpan={5} />
                  <td>
                    <button
                      type="button"
                      className="primary-button"
                      disabled={submitting}
                      onClick={() => submitEdit(participant.participantId)}
                    >
                      保存
                    </button>
                    <button type="button" className="link-button" disabled={submitting} onClick={cancelEdit}>
                      キャンセル
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={participant.participantId}>
                  <td>{participant.grade}</td>
                  <td>{participant.name}</td>
                  <td>{participant.isNew ? "新規" : "既存"}</td>
                  <td>{participant.isNew ? "-" : participant.visitCount}</td>
                  <td>{!participant.isNew && participant.previousDate ? formatDateWithWeekday(participant.previousDate) : "-"}</td>
                  {isAdmin && <td>{participant.inputBy === "self" ? "本人入力" : "代理入力"}</td>}
                  {isAdmin && <td>{new Date(participant.checkedInAt).toLocaleTimeString("ja-JP")}</td>}
                  {isAdmin && (
                    <td className="stack-row">
                      <button type="button" className="secondary-button" onClick={() => startEdit(participant)}>
                        編集
                      </button>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => deleteParticipant(participant.participantId)}
                      >
                        削除
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
          </tbody>
        </table>
        {session && session.participants.length === 0 && <p>まだ参加者はいません</p>}
      </div>

      {proxyStep.name === "idle" && (
        <button type="button" className="secondary-button" onClick={() => setProxyStep({ name: "form" })}>
          代理入力する
        </button>
      )}

      {proxyStep.name === "form" && (
        <div className="card">
          <h2>代理入力</h2>
          <p className="review-hint">保護者が不在の場合などに、指導者が代わりに登録します。</p>
          <ChildrenForm
            targetGrades={classInfo?.targetGrades ?? GRADES}
            submitLabel="確認へ進む"
            submitting={submitting}
            onSubmit={submitProxyChildren}
          />
        </div>
      )}

      {proxyStep.name === "review" && (
        <CheckinReview
          items={proxyStep.items}
          childRows={proxyStep.childRows}
          submitting={submitting}
          onBack={() => setProxyStep({ name: "form" })}
          onConfirm={submitProxyConfirmations}
        />
      )}
    </div>
  );
}
