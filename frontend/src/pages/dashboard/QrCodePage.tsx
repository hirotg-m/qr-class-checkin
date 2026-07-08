import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import QRCode from "qrcode";
import { get } from "../../api/client";
import type { ClassSummary, MonthlyPin } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { currentMonth } from "../../lib/date";

export function QrCodePage() {
  const { classId = "" } = useParams<{ classId: string }>();
  const { auth } = useAuth();
  const token = auth?.token;

  const [classInfo, setClassInfo] = useState<ClassSummary | null>(null);
  const [pin, setPin] = useState<MonthlyPin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const checkinUrl = `${window.location.origin}/c/${classId}`;

  useEffect(() => {
    get<ClassSummary[]>("/classes", token)
      .then((list) => setClassInfo(list.find((c) => c.classId === classId) ?? null))
      .catch(() => undefined);
  }, [classId, token]);

  useEffect(() => {
    get<MonthlyPin>(`/classes/${classId}/pin/${currentMonth()}`, token)
      .then(setPin)
      .catch(() => setPin(null));
  }, [classId, token]);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, checkinUrl, { width: 320, margin: 2 }).catch(() =>
      setError("QRコードの生成に失敗しました"),
    );
  }, [checkinUrl]);

  const downloadPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `qr-${classId}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  return (
    <div className="page centered">
      <h1>{classInfo ? `${classInfo.name}のQRコード` : "QRコード"}</h1>
      <p>会場の入口に掲示してください。保護者がこのQRコードを読み取ると参加登録フォームが開きます。</p>

      {error && <p className="error-text">{error}</p>}

      <div className="card qr-card">
        <canvas ref={canvasRef} />
      </div>

      <p className="qr-pin">今月のPIN：{pin?.pin ?? "未設定"}</p>
      <p className="qr-url">{checkinUrl}</p>

      <div className="stack-row qr-actions">
        <button type="button" className="secondary-button" onClick={downloadPng}>
          PNGをダウンロード
        </button>
        <button type="button" className="secondary-button" onClick={() => window.print()}>
          印刷
        </button>
      </div>
    </div>
  );
}
