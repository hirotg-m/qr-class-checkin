# API仕様

`REQUIREMENTS.md` の要件定義に基づくREST API仕様。バックエンドはFastAPI（Lambda上でMangum経由）。

## 0. 共通仕様

### 0.1 ベースURL
API Gateway HTTP APIのエンドポイント直下（例：`https://xxxx.execute-api.ap-northeast-1.amazonaws.com`）。ステージプレフィックスは実装時に決定。

### 0.2 認証
2種類のAPI群がある。

| 種別 | 対象エンドポイント | 認証方式 |
|---|---|---|
| 公開API | `/public/*` | 認証なし。月次PINをリクエストボディで都度検証 |
| 指導者・管理者API | それ以外すべて | `Authorization: Bearer <JWT>`。`role`クレームが`viewer`（指導者）または`admin`（管理者） |

管理者専用エンドポイントは`role: admin`以外だと`403 FORBIDDEN`。

### 0.3 共通エラーレスポンス
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "人が読めるエラーメッセージ",
    "index": null
  }
}
```
`index`は、きょうだいをまとめて送信する`children`/`confirmations`配列の一部でのみ発生したエラー（例：ある子どもだけ学年が対象外）の場合に、その配列内の位置を示す。送信全体に関わるエラー（PIN不一致・受付時間外など）では`null`。

| HTTPステータス | `code`例 | 説明 |
|---|---|---|
| 400 | `VALIDATION_ERROR` | リクエスト形式・値の不正 |
| 400 | `GRADE_NOT_ALLOWED` | 学年がクラスの対象学年範囲外 |
| 401 | `UNAUTHORIZED` | JWT欠落・無効・期限切れ |
| 401 | `INVALID_PIN` | 月次PIN不一致 |
| 403 | `FORBIDDEN` | 権限不足（`viewer`が管理者専用APIを呼んだ等） |
| 403 | `OUTSIDE_RECEPTION_HOURS` | 受付時間外（活動開始30分前〜終了時刻の範囲外） |
| 404 | `NOT_FOUND` | 対象リソースが存在しない |
| 409 | `CONFLICT` | 同一日の活動予定重複など |
| 429 | `RATE_LIMITED` | ログイン試行のレート制限超過（8.2節） |
| 500 | `INTERNAL_ERROR` | サーバー内部エラー |

### 0.4 日時形式
- 日付：`YYYY-MM-DD`
- 時刻：`HH:mm`（24時間表記、会場ローカル時刻）
- 日時：ISO 8601（例：`2026-07-07T16:03:00+09:00`）

### 0.5 学年の値
`小1`〜`小6`、`中1`〜`中3`の固定値セット。`Classes.targetGrades`はこの部分集合。

---

## 1. 公開API（保護者向け、認証なし）

QRコードから遷移するクラス固定のランディングページ〜参加登録までを扱う。`REQUIREMENTS.md` 3.3節に対応。認証は行わないが、月次PINと受付時間・対象学年をサーバー側で必ず再検証する。

QRコードはクラスごとに異なるものを掲示する（例：月曜17:00-18:00のクラスAと、同じ会場の別クラスとで別のQR）。QRコードが指すのはAPIエンドポイントではなく、`classId`を含んだフロントエンドのURL（例：`https://<frontend-domain>/c/{classId}`）。フロントエンドはこの`classId`を使って`1.1`以降の公開APIを呼び出す。

### 1.1 `GET /public/classes/{classId}`
QR読み取り直後に表示する情報を取得する。PIN不要（クラス名・対象学年・本日の受付可否のみ返す。参加者名簿等の個人情報は含まない）。

**レスポンス 200**
```json
{
  "classId": "c_001",
  "className": "少年サッカークラス",
  "targetGrades": ["小1", "小2", "小3", "小4", "小5", "小6"],
  "todaySession": {
    "date": "2026-07-07",
    "startTime": "16:00",
    "endTime": "17:00",
    "acceptingNow": true
  }
}
```
`todaySession`は当日`Schedule`が存在しない場合`null`。`acceptingNow`は「活動開始30分前〜終了時刻」内かどうかのサーバー側判定結果。

**エラー**：`404 NOT_FOUND`（classIdが存在しない）

### 1.2 `POST /public/classes/{classId}/pin`
保護者がPINを入力する画面で呼ぶ。PINが正しければ、以降の登録操作に使う短命トークン`checkinToken`を発行する。学年・氏名の入力欄は、このAPIが成功するまでフロントエンドで表示・活性化しない。

**リクエスト**
```json
{ "pin": "1234" }
```

**レスポンス 200**
```json
{ "checkinToken": "<token>", "expiresIn": 600 }
```
`checkinToken`は対象`classId`に紐づくJWTで、有効期限は10分（`expiresIn`秒）。指導者・管理者用のログイントークン（8.2節）とは別物で、`type: "checkin"`クレームを持ち、書き込み系以外のAPI（`/classes`のCRUD等）には使えない。

**エラー**：`401 INVALID_PIN`（PIN不一致）、`404 NOT_FOUND`（classIdが存在しない）

PIN自体には8.2節のようなログイン試行レート制限は設けない（数字4桁程度の総当たりは考慮するが、保護者の入力ミスで長時間ロックすると運用上支障が出るため）。今後、同一IPからの短時間大量試行が問題になった場合は`LoginAttempts`と同様の仕組みの追加を検討する（`REQUIREMENTS.md` 6節）。

### 1.3 `POST /public/classes/{classId}/checkin`
`checkinToken`を使い、子どもの学年／氏名を送信して参加者名簿と照合する。1人の保護者が複数の子ども（きょうだい）をまとめて登録できるよう、`children`は配列で受け取る（1人のみでも配列で送る）。表記ゆれがあれば候補提示、なければ新規/既存を確定する（`1.4`で最終確定）。

**リクエスト**
```json
{
  "checkinToken": "<token>",
  "children": [
    { "name": "山田太郎", "grade": "小5" },
    { "name": "山田花子", "grade": "小2" }
  ],
  "inputBy": "self"
}
```
`inputBy`は`"self"`（保護者本人）または`"proxy"`（指導者代理・フォールバック時。3.3節）。同一送信内の全員に共通で適用する。

**サーバー側の検証順序**
1. `checkinToken`が有効か（`classId`一致・未失効。無効な場合は`401 UNAUTHORIZED`）
2. 受付時間内か（範囲外は`403 OUTSIDE_RECEPTION_HOURS`）
3. `children`各要素の`grade`がクラスの`targetGrades`に含まれるか（1人でも含まれない場合、該当`index`を添えて`400 GRADE_NOT_ALLOWED`とし送信全体を拒否する）
4. 上記を満たせば`children`の各要素を独立に名簿とマッチング（きょうだい同士は互いに照合しない）

**レスポンス 200**
```json
{
  "results": [
    { "index": 0, "status": "confirmed", "participantId": "p_123", "isNew": false },
    {
      "index": 1,
      "status": "candidates",
      "candidates": [
        { "participantId": "p_789", "name": "山田花子", "grade": "小2" },
        { "participantId": "p_790", "name": "山田華子", "grade": "小2" }
      ]
    }
  ]
}
```
`status`は子どもごとに`"confirmed"`（完全一致・不一致なし）／`"candidates"`（表記ゆれ候補あり）／`"new"`（一致なし＝新規、`proposedName`・`proposedGrade`を含む）のいずれか。`index`は`children`配列内の位置に対応する。

この時点ではまだ`SessionLog`・`Participants`への書き込みは行わない（確認画面で保護者が目視確認してから`1.4`で確定）。

### 1.4 `POST /public/classes/{classId}/checkin/confirm`
確認画面での最終確定。子どもごとに候補から選択、または新規登録として確定し、`SessionLog`（新規の場合は`Participants`も）に書き込む。

**リクエスト**
```json
{
  "checkinToken": "<token>",
  "confirmations": [
    { "index": 0, "action": "select_existing", "participantId": "p_123" },
    { "index": 1, "action": "create_new", "name": "山田花子", "grade": "小2" }
  ],
  "inputBy": "self"
}
```
`index`は`1.3`のレスポンスにおける`index`と対応させる。`checkinToken`・受付時間・対象学年は`1.3`と同様に再検証する（画面表示から確定までの間に月やスケジュールが変わるケースを考慮）。

**レスポンス 201**
```json
{
  "results": [
    { "index": 0, "participantId": "p_123", "isNew": false, "checkedInAt": "2026-07-07T16:03:00+09:00" },
    { "index": 1, "participantId": "p_791", "isNew": true, "checkedInAt": "2026-07-07T16:03:05+09:00" }
  ]
}
```
一部の子どものみ書き込みに失敗した場合（例：`409 CONFLICT`が一部の`index`のみで発生）でも、成功した子どもの書き込みはロールバックしない。エラーは`error.index`で対象を示し、保護者側は失敗した子どものみ再送信する。

**エラー**：`401 UNAUTHORIZED`（`checkinToken`が無効・期限切れ）、`403 OUTSIDE_RECEPTION_HOURS`、`400 GRADE_NOT_ALLOWED`、`404 NOT_FOUND`（`participantId`不正）、`409 CONFLICT`（同日同一参加者が既に来場記録済み）。いずれも該当する`index`を`error.index`に含める。

`checkinToken`が`1.3`と`1.4`の間に失効した場合、保護者は`1.2`からやり直す（入力済みの氏名・学年はフロントエンドで保持し再送信を省力化する）。

---

## 2. 認証API

### 2.1 `POST /auth/login`
指導者用・管理者用いずれの8桁コードも同一エンドポイントで受け付け、コードの種類に応じて`role`を決定する。

**リクエスト**
```json
{ "code": "12345678" }
```

**レスポンス 200**
```json
{ "token": "<JWT>", "role": "viewer", "expiresIn": 28800 }
```
`role`は`"viewer"`（指導者コード）または`"admin"`（管理者コード）。`expiresIn`は秒（8時間＝28800）。

**エラー**
- `401 UNAUTHORIZED`：コード不一致
- `429 RATE_LIMITED`：同一IPから3分間に10回失敗（8.2節。`LoginAttempts`テーブルで管理）

---

## 3. クラス管理API

閲覧は`viewer`・`admin`共通、作成・更新・削除は`admin`のみ。

### 3.1 `GET /classes`
**レスポンス 200**
```json
[
  {
    "classId": "c_001",
    "name": "少年サッカークラス",
    "description": "小学生対象の週1回クラス",
    "targetGrades": ["小1", "小2", "小3", "小4", "小5", "小6"]
  }
]
```

### 3.2 `POST /classes`（admin）
**リクエスト**
```json
{
  "name": "少年サッカークラス",
  "description": "小学生対象の週1回クラス",
  "targetGrades": ["小1", "小2", "小3", "小4", "小5", "小6"]
}
```
**レスポンス 201**：作成された`classId`を含む3.1と同じ形式のオブジェクト

### 3.3 `PUT /classes/{classId}`（admin）
リクエスト・レスポンスは3.2と同じ形式。**レスポンス 200**

### 3.4 `DELETE /classes/{classId}`（admin）
**レスポンス 204**（本文なし）。関連する`Schedule`/`MonthlyPin`/`Participants`/`SessionLog`が残る場合の扱いは未決（`REQUIREMENTS.md` 6節に追記候補）。

---

## 4. 活動予定・月次PIN API

### 4.1 `GET /classes/{classId}/schedule?month=yyyy-mm`
**レスポンス 200**
```json
[
  { "date": "2026-07-07", "startTime": "16:00", "endTime": "17:00", "location": "第一体育館" }
]
```

### 4.2 `POST /classes/{classId}/schedule`（admin）
**リクエスト**
```json
{ "date": "2026-07-07", "startTime": "16:00", "endTime": "17:00", "location": "第一体育館" }
```
**レスポンス 201**。同一`date`が既存の場合`409 CONFLICT`。

### 4.3 `PUT /classes/{classId}/schedule/{date}`（admin）
リクエストは4.2と同じ形式（`date`除く）。**レスポンス 200**

### 4.4 `DELETE /classes/{classId}/schedule/{date}`（admin）
**レスポンス 204**

### 4.5 `GET /classes/{classId}/pin/{yyyy-mm}`
QRコード掲示物にPINを記載する用途など、指導者・管理者が現在設定されているPINを確認するためのエンドポイント（保護者向けの照合はPIN自体を返さない`1.2`を使う）。

**レスポンス 200**
```json
{ "classId": "c_001", "month": "2026-07", "pin": "1234" }
```
未設定の月は`pin: null`。

### 4.6 `PUT /classes/{classId}/pin/{yyyy-mm}`（admin）
**リクエスト**
```json
{ "pin": "1234" }
```
**レスポンス 200**

---

## 5. 参加状況API

### 5.1 `GET /classes/{classId}/sessions/{date}`
`participants`は学年順（小1→中3）、同学年内は氏名順で返す。

**レスポンス 200**
```json
{
  "date": "2026-07-07",
  "schedule": { "startTime": "16:00", "endTime": "17:00", "location": "第一体育館" },
  "participants": [
    {
      "participantId": "p_123",
      "name": "山田太郎",
      "grade": "小5",
      "isNew": false,
      "checkedInAt": "2026-07-07T16:03:00+09:00",
      "inputBy": "self",
      "visitCount": 2,
      "previousDate": "2026-06-30"
    }
  ]
}
```
`visitCount`はこの日より前にそのクラスへ参加した回数（この日自体は含まない）。`previousDate`は今回より前の直近の参加日（初回参加の場合は`visitCount`が`0`、`previousDate`が`null`）。参加者ごとに`SessionLog`を横断集計するため、クラス規模が大きくなると負荷が増える点に注意（`REQUIREMENTS.md` 6節の将来検討事項）。

### 5.2 `POST /classes/{classId}/sessions/{date}/proxy`
指導者による代理入力。指導者(`viewer`)・管理者(`admin`)どちらのトークンでも呼び出し可。きょうだいをまとめて代理入力できるよう`children`は配列（`1.3`と同じ形）。ロジックは公開APIの`1.3`と同じマッチングを内部的に共有する。認証済みのAPIのため、PIN・`checkinToken`は不要。

`viewer`は公開APIと同じ受付時間チェック（開始30分前〜終了時刻）が適用されるが、`admin`は過去日の記録修正のためこのチェックを受けない（`{date}`が任意の過去日でも呼び出せる）。

**リクエスト**
```json
{
  "children": [
    { "name": "山田太郎", "grade": "小5" },
    { "name": "山田花子", "grade": "小2" }
  ]
}
```

**レスポンス 200**：`1.3`と同じ形式（`results`配列、`index`ごとに`confirmed` / `candidates` / `new`）

### 5.3 `POST /classes/{classId}/sessions/{date}/proxy/confirm`
**リクエスト**
```json
{
  "confirmations": [
    { "index": 0, "action": "select_existing", "participantId": "p_123" },
    { "index": 1, "action": "create_new", "name": "山田花子", "grade": "小2" }
  ]
}
```
`inputBy`は常に`"proxy"`固定でサーバー側が設定する。

**レスポンス 201**：`1.4`と同じ形式（`results`配列）

`viewer`/`admin`の受付時間チェックの扱いは`5.2`と同じ。

### 5.4 `DELETE /classes/{classId}/sessions/{date}/participants/{participantId}`（admin）
誤って登録した来場記録の取り消し。`SessionLog`のその日の記録のみ削除し、`Participants`名簿からは削除しない。

**レスポンス 204**（本文なし）

### 5.5 `PUT /classes/{classId}/participants/{participantId}`（admin）
参加者の氏名・学年の訂正（表記ゆれ・入力ミス対応）。全期間の記録に影響する（`Participants`名簿を直接更新するため、`SessionLog`側の過去の表示にも反映される）。

**リクエスト**
```json
{ "name": "山田太郎", "grade": "小5" }
```
**レスポンス 200**
```json
{ "participantId": "p_123", "name": "山田太郎", "grade": "小5", "firstSeenDate": "2026-06-01" }
```
学年がクラスの対象学年外の場合は`400 GRADE_NOT_ALLOWED`。

### 5.6 `GET /classes/{classId}/participants`
クラスの参加者名簿一覧（`viewer`/`admin`共通、編集は`5.5`でadminのみ）。学年・氏名順にソートして返す。

**レスポンス 200**
```json
[
  { "participantId": "p_123", "name": "山田太郎", "grade": "小5", "firstSeenDate": "2026-06-01", "visitCount": 4 }
]
```

### 5.7 `DELETE /classes/{classId}/participants/{participantId}`（admin）
参加者名簿からの削除。`SessionLog`の過去の記録自体は消さないが、参加者名を引けなくなるため参加者一覧・統計には以後表示されなくなる（`Classes`削除時と同様、関連レコードの扱いは`REQUIREMENTS.md` 6節の未決事項）。

**レスポンス 204**（本文なし）

---

## 6. 統計API

### 6.1 `GET /classes/{classId}/stats/participants?from=&to=`
**レスポンス 200**
```json
[
  { "date": "2026-06-01", "total": 18, "byGrade": { "小1": 3, "小2": 5, "小3": 4, "小4": 2, "小5": 3, "小6": 1 } }
]
```
`from`/`to`は`YYYY-MM-DD`。集計は`SessionLog`をクラス・期間指定でクエリし、Lambda側で学年ごとに件数を集計する（`REQUIREMENTS.md` 9.2節）。

---

## 7. エンドポイント一覧（早見表）

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `/public/classes/{classId}` | なし | クラス情報・本日の受付可否取得 |
| POST | `/public/classes/{classId}/pin` | なし | PIN検証、`checkinToken`発行 |
| POST | `/public/classes/{classId}/checkin` | checkinToken | 参加登録（照合） |
| POST | `/public/classes/{classId}/checkin/confirm` | checkinToken | 参加登録（確定） |
| POST | `/auth/login` | なし | ログイン |
| GET | `/classes` | viewer/admin | クラス一覧 |
| POST | `/classes` | admin | クラス作成 |
| PUT | `/classes/{classId}` | admin | クラス編集 |
| DELETE | `/classes/{classId}` | admin | クラス削除 |
| GET | `/classes/{classId}/schedule` | viewer/admin | 活動予定取得 |
| POST | `/classes/{classId}/schedule` | admin | 活動予定追加 |
| PUT | `/classes/{classId}/schedule/{date}` | admin | 活動予定編集 |
| DELETE | `/classes/{classId}/schedule/{date}` | admin | 活動予定削除 |
| GET | `/classes/{classId}/pin/{yyyy-mm}` | viewer/admin | 月次PIN確認 |
| PUT | `/classes/{classId}/pin/{yyyy-mm}` | admin | 月次PIN設定 |
| GET | `/classes/{classId}/sessions/{date}` | viewer/admin | 参加者一覧 |
| POST | `/classes/{classId}/sessions/{date}/proxy` | viewer/admin | 代理入力（照合） |
| POST | `/classes/{classId}/sessions/{date}/proxy/confirm` | viewer/admin | 代理入力（確定。adminは受付時間外も可） |
| DELETE | `/classes/{classId}/sessions/{date}/participants/{participantId}` | admin | 来場記録の取り消し |
| PUT | `/classes/{classId}/participants/{participantId}` | admin | 参加者の氏名・学年修正 |
| GET | `/classes/{classId}/participants` | viewer/admin | 参加者名簿一覧 |
| DELETE | `/classes/{classId}/participants/{participantId}` | admin | 参加者名簿からの削除 |
| GET | `/classes/{classId}/stats/participants` | viewer/admin | 参加人数統計 |
