import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { extractMessage, post } from "../../api/client";
import type { Role } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { CodeInput } from "../../components/CodeInput";

const CODE_LENGTH = 8;
const ORG_NAME = import.meta.env.VITE_ORG_NAME;

export function LoginPage() {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    post<{ token: string; role: Role; expiresIn: number }>("/auth/login", { code })
      .then((res) => {
        login(res.token, res.role);
        navigate("/dashboard");
      })
      .catch((err: unknown) => setError(extractMessage(err, "ログインに失敗しました")))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="page centered">
      {ORG_NAME && <p className="org-name">{ORG_NAME}</p>}
      <h1>指導者・管理者ログイン</h1>
      <form className="stack" onSubmit={handleSubmit}>
        <label className="field code-field">
          <span>8桁コード</span>
          <CodeInput length={CODE_LENGTH} value={code} onChange={setCode} disabled={submitting} autoFocus />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button
          type="submit"
          className="primary-button login-button"
          disabled={submitting || code.length !== CODE_LENGTH}
        >
          {submitting ? "確認中…" : "ログイン"}
        </button>
      </form>
    </div>
  );
}
