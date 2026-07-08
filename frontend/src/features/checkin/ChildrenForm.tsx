import { useState } from "react";
import type { ChildRow } from "../../api/types";

type Props = {
  targetGrades: string[];
  submitLabel: string;
  submitting: boolean;
  onSubmit: (children: ChildRow[]) => void;
};

function emptyRow(defaultGrade: string): ChildRow {
  return { name: "", grade: defaultGrade };
}

export function ChildrenForm({ targetGrades, submitLabel, submitting, onSubmit }: Props) {
  const defaultGrade = targetGrades[0] ?? "";
  const [rows, setRows] = useState<ChildRow[]>([emptyRow(defaultGrade)]);

  const updateRow = (index: number, patch: Partial<ChildRow>) => {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  };

  const addRow = () => setRows((prev) => [...prev, emptyRow(defaultGrade)]);

  const removeRow = (index: number) => setRows((prev) => prev.filter((_, i) => i !== index));

  const canSubmit = rows.length > 0 && rows.every((row) => row.name.trim().length > 0 && row.grade);

  return (
    <form
      className="stack"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(rows.map((row) => ({ name: row.name.trim(), grade: row.grade })));
      }}
    >
      {rows.map((row, index) => (
        <div className="card child-row" key={index}>
          <div className="child-row-header">
            <span>{index === 0 ? "お子さま" : `お子さま（${index + 1}人目）`}</span>
            {rows.length > 1 && (
              <button
                type="button"
                className="link-button"
                onClick={() => removeRow(index)}
                aria-label="この子どもを削除"
              >
                削除
              </button>
            )}
          </div>
          <label className="field">
            <span>学年</span>
            <select value={row.grade} onChange={(event) => updateRow(index, { grade: event.target.value })} required>
              {targetGrades.map((grade) => (
                <option key={grade} value={grade}>
                  {grade}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>氏名</span>
            <input
              type="text"
              value={row.name}
              onChange={(event) => updateRow(index, { name: event.target.value })}
              placeholder="例：山田太郎"
              required
            />
          </label>
        </div>
      ))}

      <button type="button" className="secondary-button" onClick={addRow}>
        + きょうだいを追加
      </button>

      <button type="submit" className="primary-button" disabled={!canSubmit || submitting}>
        {submitting ? "確認中…" : submitLabel}
      </button>
    </form>
  );
}
