// docs/api.md のスキーマに対応する型定義

export type TodaySession = {
  date: string;
  startTime: string;
  endTime: string;
  acceptingNow: boolean;
};

export type ClassInfo = {
  classId: string;
  className: string;
  targetGrades: string[];
  todaySession: TodaySession | null;
};

export type ChildRow = {
  name: string;
  grade: string;
};

export type Candidate = {
  participantId: string;
  name: string;
  grade: string;
};

// docs/api.md 1.3節/5.2節: statusごとにフィールドが変わるレスポンス項目
export type CheckinResultItem = {
  index: number;
  status: "confirmed" | "candidates" | "new";
  participantId: string | null;
  isNew: boolean | null;
  candidates: Candidate[] | null;
  proposedName: string | null;
  proposedGrade: string | null;
};

export type ConfirmationPayload =
  | { index: number; action: "select_existing"; participantId: string }
  | { index: number; action: "create_new"; name: string; grade: string };

export type CheckinConfirmResultItem = {
  index: number;
  participantId: string;
  isNew: boolean;
  checkedInAt: string;
};

export type Role = "viewer" | "admin";

export type ClassSummary = {
  classId: string;
  name: string;
  description: string;
  targetGrades: string[];
};

export type MonthlyPin = {
  classId: string;
  month: string;
  pin: string | null;
};

export type ParticipantListItem = {
  participantId: string;
  name: string;
  grade: string;
  firstSeenDate: string | null;
  visitCount: number;
};

export type ScheduleEntry = {
  date: string;
  startTime: string;
  endTime: string;
  location: string;
};

export type ParticipantView = {
  participantId: string;
  name: string;
  grade: string;
  isNew: boolean;
  checkedInAt: string;
  inputBy: "self" | "proxy";
  visitCount: number;
  previousDate: string | null;
};

export type SessionDetail = {
  date: string;
  schedule: ScheduleEntry | null;
  participants: ParticipantView[];
};

export type StatsEntry = {
  date: string;
  total: number;
  byGrade: Record<string, number>;
};
