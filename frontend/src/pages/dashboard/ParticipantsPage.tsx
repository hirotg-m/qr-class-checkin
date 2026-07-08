import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { del, extractMessage, get, put } from "../../api/client";
import type { ClassSummary, ParticipantListItem } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { GRADES } from "../../features/checkin/grades";
import { formatDateWithWeekday } from "../../lib/date";

type EditForm = { name: string; grade: string };

export function ParticipantsPage() {
  const { classId = "" } = useParams<{ classId: string }>();
  const { auth } = useAuth();
  const token = auth?.token;
  const isAdmin = auth?.role === "admin";

  const [classInfo, setClassInfo] = useState<ClassSummary | null>(null);
  const [participants, setParticipants] = useState<ParticipantListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ name: "", grade: "" });
  const [submitting, setSubmitting] = useState(false);

  const loadParticipants = () => {
    get<ParticipantListItem[]>(`/classes/${classId}/participants`, token)
      .then(setParticipants)
      .catch(() => setError("参加者名簿の取得に失敗しました"));
  };

  useEffect(loadParticipants, [classId, token]);

  useEffect(() => {
    get<ClassSummary[]>("/classes", token)
      .then((list) => setClassInfo(list.find((c) => c.classId === classId) ?? null))
      .catch(() => undefined);
  }, [classId, token]);

  const startEdit = (participant: ParticipantListItem) => {
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
        loadParticipants();
      })
      .catch((err: unknown) => setError(extractMessage(err, "参加者情報の修正に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  const deleteParticipant = (participantId: string) => {
    if (
      !window.confirm(
        "この参加者を名簿から削除しますか？（過去の来場記録は残りますが、一覧・統計には表示されなくなります）",
      )
    )
      return;
    setSubmitting(true);
    setError(null);
    del(`/classes/${classId}/participants/${participantId}`, token)
      .then(loadParticipants)
      .catch((err: unknown) => setError(extractMessage(err, "参加者の削除に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="page page-wide">
      <h1>{classInfo ? `${classInfo.name} 参加者名簿` : "参加者名簿"}</h1>
      {error && <p className="error-text">{error}</p>}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>学年</th>
              <th>氏名</th>
              <th>初回参加日</th>
              <th>参加回数</th>
              {isAdmin && <th>操作</th>}
            </tr>
          </thead>
          <tbody>
            {(participants ?? []).map((participant) =>
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
                  <td colSpan={2} />
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
                  <td>{participant.firstSeenDate ? formatDateWithWeekday(participant.firstSeenDate) : "-"}</td>
                  <td>{participant.visitCount}</td>
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
        {participants && participants.length === 0 && <p>まだ参加者はいません</p>}
      </div>
    </div>
  );
}
