import { type ReactNode, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError, extractMessage, get, post } from "../../api/client";
import type {
  CheckinConfirmResultItem,
  CheckinResultItem,
  ChildRow,
  ClassInfo,
  ConfirmationPayload,
} from "../../api/types";
import { ChildrenForm } from "../../features/checkin/ChildrenForm";
import { CheckinReview } from "../../features/checkin/CheckinReview";

type Step =
  | { name: "loading" }
  | { name: "load-error"; message: string }
  | { name: "not-accepting"; info: ClassInfo }
  | { name: "pin"; info: ClassInfo }
  | { name: "children"; info: ClassInfo; checkinToken: string }
  | { name: "review"; info: ClassInfo; checkinToken: string; childRows: ChildRow[]; items: CheckinResultItem[] }
  | { name: "complete"; results: CheckinConfirmResultItem[] };

export function CheckinWizard() {
  const { classId = "" } = useParams<{ classId: string }>();
  const [step, setStep] = useState<Step>({ name: "loading" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStep({ name: "loading" });
    get<ClassInfo>(`/public/classes/${classId}`)
      .then((info) => {
        if (cancelled) return;
        setStep(info.todaySession?.acceptingNow ? { name: "pin", info } : { name: "not-accepting", info });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setStep({ name: "load-error", message: extractMessage(err, "クラス情報の取得に失敗しました") });
      });
    return () => {
      cancelled = true;
    };
  }, [classId]);

  const verifyPin = (pin: string, info: ClassInfo) => {
    setSubmitting(true);
    setError(null);
    post<{ checkinToken: string }>(`/public/classes/${classId}/pin`, { pin })
      .then((res) => setStep({ name: "children", info, checkinToken: res.checkinToken }))
      .catch((err: unknown) => setError(extractMessage(err, "PINの確認に失敗しました")))
      .finally(() => setSubmitting(false));
  };

  const submitChildren = (childRows: ChildRow[], info: ClassInfo, checkinToken: string) => {
    setSubmitting(true);
    setError(null);
    post<{ results: CheckinResultItem[] }>(`/public/classes/${classId}/checkin`, {
      checkinToken,
      children: childRows,
      inputBy: "self",
    })
      .then((res) => setStep({ name: "review", info, checkinToken, childRows, items: res.results }))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.code === "UNAUTHORIZED") {
          setStep({ name: "pin", info });
          setError("入力に時間がかかったため、もう一度PINを入力してください");
          return;
        }
        setError(extractMessage(err, "参加者の照合に失敗しました"));
      })
      .finally(() => setSubmitting(false));
  };

  const submitConfirmations = (confirmations: ConfirmationPayload[], info: ClassInfo, checkinToken: string) => {
    setSubmitting(true);
    setError(null);
    post<{ results: CheckinConfirmResultItem[] }>(`/public/classes/${classId}/checkin/confirm`, {
      checkinToken,
      confirmations,
      inputBy: "self",
    })
      .then((res) => setStep({ name: "complete", results: res.results }))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.code === "UNAUTHORIZED") {
          setStep({ name: "pin", info });
          setError("入力に時間がかかったため、もう一度PINを入力してください");
          return;
        }
        setError(extractMessage(err, "来場登録に失敗しました"));
      })
      .finally(() => setSubmitting(false));
  };

  switch (step.name) {
    case "loading":
      return <Centered>読み込み中…</Centered>;

    case "load-error":
      return <Centered>{step.message}</Centered>;

    case "not-accepting":
      return (
        <Centered>
          <h1>{step.info.className}</h1>
          <p>現在は受付時間外です。活動開始30分前になりましたら再度お試しください。</p>
        </Centered>
      );

    case "pin":
      return (
        <div className="page">
          <h1>{step.info.className}</h1>
          <p>会場に掲示されている今月の暗証番号を入力してください。</p>
          {error && <p className="error-text">{error}</p>}
          <PinForm submitting={submitting} onSubmit={(pin) => verifyPin(pin, step.info)} />
        </div>
      );

    case "children":
      return (
        <div className="page">
          <h1>{step.info.className}</h1>
          <p>参加するお子さまの学年・氏名を入力してください。きょうだいがいる場合はまとめて入力できます。</p>
          {error && <p className="error-text">{error}</p>}
          <ChildrenForm
            targetGrades={step.info.targetGrades}
            submitLabel="次へ（確認画面へ）"
            submitting={submitting}
            onSubmit={(childRows) => submitChildren(childRows, step.info, step.checkinToken)}
          />
        </div>
      );

    case "review":
      return (
        <div className="page">
          <h1>{step.info.className}</h1>
          {error && <p className="error-text">{error}</p>}
          <CheckinReview
            items={step.items}
            childRows={step.childRows}
            submitting={submitting}
            onBack={() => setStep({ name: "children", info: step.info, checkinToken: step.checkinToken })}
            onConfirm={(confirmations) => submitConfirmations(confirmations, step.info, step.checkinToken)}
          />
        </div>
      );

    case "complete":
      return (
        <Centered>
          <h1>来場記録が完了しました</h1>
          <ul className="stack plain-list">
            {step.results.map((result) => (
              <li key={result.index} className="card">
                来場を記録しました（{result.isNew ? "新規登録" : "登録済みの参加者"}）
              </li>
            ))}
          </ul>
        </Centered>
      );
  }
}

function Centered({ children }: { children: ReactNode }) {
  return <div className="page centered">{children}</div>;
}

function PinForm({ submitting, onSubmit }: { submitting: boolean; onSubmit: (pin: string) => void }) {
  const [pin, setPin] = useState("");
  return (
    <form
      className="stack"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(pin);
      }}
    >
      <label className="field">
        <span>暗証番号（PIN）</span>
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
        {submitting ? "確認中…" : "次へ"}
      </button>
    </form>
  );
}
