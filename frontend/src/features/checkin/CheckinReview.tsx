import { useState } from "react";
import type { CheckinResultItem, ChildRow, ConfirmationPayload } from "../../api/types";

type Choice = { kind: "pending" } | { kind: "confirmed" } | { kind: "candidate"; participantId: string } | { kind: "new" };

type Props = {
  items: CheckinResultItem[];
  childRows: ChildRow[];
  submitting: boolean;
  onConfirm: (confirmations: ConfirmationPayload[]) => void;
  onBack: () => void;
};

// 新規登録の場合も含め、確定確認まではSessionLog/Participantsへの書き込みを行わない
// （docs/api.md 1.3節/1.4節）。ここでは特に「新規」の場合に必ず明示チェックを求める。
export function CheckinReview({ items, childRows, submitting, onConfirm, onBack }: Props) {
  const [choices, setChoices] = useState<Record<number, Choice>>(() => {
    const initial: Record<number, Choice> = {};
    for (const item of items) {
      initial[item.index] = { kind: "pending" };
    }
    return initial;
  });

  const setChoice = (index: number, choice: Choice) => {
    setChoices((prev) => ({ ...prev, [index]: choice }));
  };

  const allResolved = items.every((item) => choices[item.index]?.kind !== "pending");

  const handleSubmit = () => {
    const confirmations: ConfirmationPayload[] = items.map((item) => {
      const choice = choices[item.index];
      const original = childRows[item.index];

      if (choice.kind === "candidate") {
        return { index: item.index, action: "select_existing", participantId: choice.participantId };
      }
      if (choice.kind === "confirmed" && item.participantId) {
        return { index: item.index, action: "select_existing", participantId: item.participantId };
      }
      return { index: item.index, action: "create_new", name: original.name, grade: original.grade };
    });
    onConfirm(confirmations);
  };

  return (
    <div className="stack">
      <h2>入力内容の確認</h2>

      {items.map((item) => {
        const original = childRows[item.index];
        const choice = choices[item.index];

        if (item.status === "confirmed") {
          return (
            <div className="card" key={item.index}>
              <p className="review-name">
                {original.name}（{original.grade}）
              </p>
              <p className="review-hint">名簿に登録済みの参加者として来場記録します。</p>
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={choice.kind === "confirmed"}
                  onChange={(event) =>
                    setChoice(item.index, event.target.checked ? { kind: "confirmed" } : { kind: "pending" })
                  }
                />
                この内容で間違いありません
              </label>
            </div>
          );
        }

        if (item.status === "new") {
          return (
            <div className="card" key={item.index}>
              <p className="review-name">
                {item.proposedName}（{item.proposedGrade}）
              </p>
              <p className="review-hint">名簿に見つからなかったため、新規の参加者として登録します。</p>
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={choice.kind === "new"}
                  onChange={(event) => setChoice(item.index, event.target.checked ? { kind: "new" } : { kind: "pending" })}
                />
                この内容で新規登録します
              </label>
            </div>
          );
        }

        return (
          <div className="card" key={item.index}>
            <p className="review-name">
              入力内容：{original.name}（{original.grade}）
            </p>
            <p className="review-hint">似た名前の参加者が見つかりました。該当する方を選んでください。</p>
            <div className="stack">
              {item.candidates?.map((candidate) => (
                <label className="radio-field" key={candidate.participantId}>
                  <input
                    type="radio"
                    name={`candidate-${item.index}`}
                    checked={choice.kind === "candidate" && choice.participantId === candidate.participantId}
                    onChange={() => setChoice(item.index, { kind: "candidate", participantId: candidate.participantId })}
                  />
                  {candidate.name}（{candidate.grade}）
                </label>
              ))}
              <label className="radio-field">
                <input
                  type="radio"
                  name={`candidate-${item.index}`}
                  checked={choice.kind === "new"}
                  onChange={() => setChoice(item.index, { kind: "new" })}
                />
                この中にいない（{original.name}を新規登録する）
              </label>
            </div>
          </div>
        );
      })}

      <button type="button" className="secondary-button" onClick={onBack} disabled={submitting}>
        入力し直す
      </button>
      <button type="button" className="primary-button" onClick={handleSubmit} disabled={!allResolved || submitting}>
        {submitting ? "登録中…" : "この内容で来場登録する"}
      </button>
    </div>
  );
}
