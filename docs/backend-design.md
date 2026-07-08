# バックエンド設計

`REQUIREMENTS.md`（技術構成：7.1節）・`docs/api.md`（API仕様）に基づく、FastAPIバックエンドの内部設計。

## 1. ディレクトリ構成

```text
backend/
  app/
    main.py                    # FastAPIインスタンス生成、ルーター登録、Mangumハンドラ
    api/
      deps.py                  # 認証Dependency（JWT検証、role判定）
      routers/
        public_checkin.py      # /public/classes/{classId}/... （認証なし）
        auth.py                 # /auth/login
        classes.py               # /classes ...（CRUD）
        schedule.py               # /classes/{classId}/schedule ...
        pin.py                     # /classes/{classId}/pin/{yyyy-mm}
        sessions.py                 # /classes/{classId}/sessions/{date} ...
        stats.py                     # /classes/{classId}/stats/participants
    domain/
      matching.py               # 氏名・学年の照合、表記ゆれ候補抽出ロジック
      reception_window.py       # 受付時間判定（活動開始30分前〜終了時刻）
      checkin_service.py        # 公開API・代理入力APIが共通で使うチェックイン処理
    repositories/
      classes_repo.py
      schedule_repo.py
      pin_repo.py
      participants_repo.py
      session_log_repo.py
      login_attempts_repo.py
      dynamodb.py                # boto3リソース初期化の共通化
    schemas/
      class_schemas.py
      schedule_schemas.py
      session_schemas.py
      auth_schemas.py
      common.py                  # エラーレスポンス等の共通スキーマ
    core/
      config.py                  # 環境変数・SSMパラメータの読み込み
      security.py                 # JWT発行/検証、8桁コード照合、レート制限
      errors.py                    # AppError定義とFastAPI例外ハンドラ
  tests/
    test_matching.py
    test_reception_window.py
    test_routers_*.py
  requirements.txt
  template.yaml -> ../infra/template.yaml で参照（Lambda関数定義はinfra側）
```

## 2. レイヤー構成

```text
Router（HTTP入出力・Pydanticバリデーション）
   ↓
Domain/Service（ビジネスロジック：受付時間判定・PIN照合・表記ゆれマッチング）
   ↓
Repository（DynamoDB操作、boto3）
```

- Routerは`schemas/`のPydanticモデルでリクエスト/レスポンスを検証し、Domain層を呼び出すだけに留める。
- Domain層はDynamoDBを直接触らずRepositoryを介する（テスト時にモック可能にするため）。
- Repositoryはテーブルごとに1モジュール。`Query`/`PutItem`/`UpdateItem`等の呼び出しをカプセル化する。

## 3. 認証・認可

### 3.1 Dependency設計（`api/deps.py`）
- `get_current_claims(authorization: str = Header(...))`：`Bearer <JWT>`を検証し、`{ "role": "viewer" | "admin", "exp": ... }`を返す。`type`クレームが`"checkin"`のトークン（3.4節）はここでは拒否する。失敗時は`401 UNAUTHORIZED`（`core/errors.py`のAppErrorをFastAPI例外ハンドラで変換）。
- `require_admin(claims = Depends(get_current_claims))`：`role != "admin"`なら`403 FORBIDDEN`。
- 公開API（`/public/*`）はこれらのDependencyを使わない。`GET /public/classes/{classId}`と`POST /public/classes/{classId}/pin`は無認証。`checkin`/`checkin/confirm`は`checkinToken`をリクエストボディで受け取り、専用の`verify_checkin_token`関数（3.4節）で検証する。

### 3.2 JWT（`core/security.py`）
- 署名鍵はSSM Parameter Store（SecureString）から起動時に取得し、Lambda実行環境内でキャッシュする（`core/config.py`）。
- ペイロード：`{ "role": "viewer" | "admin", "exp": <unix time> }`（`REQUIREMENTS.md` 8.2節、個人アカウントがないため`sub`は省略）。
- 有効期限8時間。

### 3.3 8桁コード照合とレート制限
- 指導者用コード・管理者用コードもSSM Parameter Store（SecureString）から取得。
- `POST /auth/login`は`login_attempts_repo`で同一IPの失敗回数をインクリメントし、3分間に10回失敗で`429 RATE_LIMITED`（`LoginAttempts`テーブル、TTLで自動クリア。`REQUIREMENTS.md` 4節）。

### 3.4 `checkinToken`（保護者向けPIN検証、`core/security.py`）
- `POST /public/classes/{classId}/pin`で`MonthlyPin`と一致した場合に発行する短命トークン。署名鍵は指導者・管理者用JWTと同じもので構わないが、ペイロードに`{ "type": "checkin", "classId": "c_001", "exp": <now+600> }`を持たせ、指導者・管理者用トークンと明確に区別する（`get_current_claims`はこの`type`を拒否し、逆に`verify_checkin_token`は`type != "checkin"`を拒否する）。
- 有効期限は10分。`checkin`/`checkin/confirm`はこのトークンの`classId`とパスパラメータの`classId`が一致することも検証する。
- 公開APIのためレート制限（3.3節）は設けない方針だが、同一IPからの異常な試行回数を監視できるよう、失敗時はログに記録する（`docs/api.md` 1.2節）。

## 4. マッチング・受付時間ロジック（`domain/`）

### 4.1 `reception_window.py`
- 対象クラスの当日`Schedule`エントリを取得し、`開始時刻 - 30分 <= 現在時刻 <= 終了時刻`を判定する純粋関数として実装（タイムゾーンは会場ローカル固定、当面はJST決め打ち）。
- `GET /public/classes/{classId}`のレスポンス生成、`checkin`/`checkin/confirm`/`proxy`の各エンドポイントから共通利用する。

### 4.2 `matching.py`
- 入力：クラスの参加者名簿（`Participants`をクラス単位で取得したリスト）、送信された`name`・`grade`。1件ずつ独立に判定する関数として実装し、きょうだいなど複数人の送信でも呼び出し側（`checkin_service.py`）でループさせるだけにする（きょうだい同士を互いに照合することはない）。
- 判定ロジック：
  1. `grade`が一致し`name`が完全一致 → 既存確定（`confirmed`）
  2. `grade`が一致し`name`が近似（編集距離が閾値以下、閾値は実装時に調整）→ 候補提示（`candidates`）
  3. 一致・近似ともになし → 新規（`new`）
- 名簿はクラスごとにスコープされているため、他クラスの参加者とは照合しない（`REQUIREMENTS.md` 4節）。

### 4.3 `checkin_service.py`
- 公開API（`1.3`/`1.4`）と代理入力API（`5.2`/`5.3`）から共通利用するサービス関数を提供し、ロジックの重複を避ける。1人の保護者が複数の子ども（きょうだい）をまとめて送信できるよう、`children`のリストを受け取りリストで返す設計とする（`docs/api.md` 1.3/1.4節）。
  - `evaluate_batch(class_id, children: list[NameGrade]) -> list[MatchResult]`：`reception_window`・対象学年チェックを送信全体に対して1回行った上で、`children`の各要素に`matching`を独立に適用し結果をリストで返す（DB書き込みなし）。
  - `confirm_batch(class_id, date, confirmations: list[Confirmation], input_by) -> list[CheckinResult]`：`confirmations`の各要素ごとに`Participants`（新規時）・`SessionLog`への書き込みを行う。一部の要素で`409 CONFLICT`等が発生しても他の要素の書き込みはロールバックせず、要素ごとの成功/失敗を結果に含める（`docs/api.md` 1.4節）。
- `checkinToken`の検証（公開APIのみ必要）はRouter側で`checkin_service`呼び出し前に、送信全体に対して1回行う（`verify_checkin_token`、3.4節）。

## 5. DynamoDBアクセスパターン

`docs/api.md`・`REQUIREMENTS.md` 4節のテーブル定義に対応。

| 操作 | テーブル | アクセス方法 |
|---|---|---|
| クラス一覧取得 | `Classes` | `Scan`（クラス数は少数想定のため許容。将来的にクラス数が増えたら要見直し） |
| クラス単体取得・作成・更新・削除 | `Classes` | `GetItem`/`PutItem`/`UpdateItem`/`DeleteItem`（`PK=CLASS#<classId>`） |
| 月内の活動予定取得 | `Schedule` | `Query`（`PK=CLASS#<classId> AND begins_with(SK, DATE#<yyyy-mm>)`） |
| 活動予定単体作成・更新・削除 | `Schedule` | `PutItem`（`ConditionExpression`で重複作成防止）/`UpdateItem`/`DeleteItem` |
| 月次PIN取得・設定 | `MonthlyPin` | `GetItem`/`PutItem`（`PK=CLASS#<classId>#MONTH#<yyyy-mm>`） |
| クラス参加者名簿取得（マッチング用） | `Participants` | `Query`（`PK=CLASS#<classId>`） |
| 参加者新規作成 | `Participants` | `PutItem`（`PK=CLASS#<classId>`, `SK=PARTICIPANT#<id>`） |
| 当日参加者一覧取得 | `SessionLog` | `Query`（`PK=CLASS#<classId>#DATE#<date>`）＋`Participants`から氏名・学年を結合 |
| 来場記録 | `SessionLog` | `PutItem`（`ConditionExpression`で同日重複チェックイン防止） |
| 統計集計 | `SessionLog` | `Query`をクラス・日付範囲で複数回、または`GSI`（クラス×日付範囲）を検討。初期はクラスごとに日付ループでQueryし件数集計（`REQUIREMENTS.md` 9.2節、事前集計テーブル不要の方針） |
| ログイン失敗回数 | `LoginAttempts` | `UpdateItem`（`ADD`でカウントアップ、`TTL`属性で自動失効） |

## 6. エラーハンドリング（`core/errors.py`）

- `AppError(code: str, status_code: int, message: str, index: int | None = None)`を定義し、Domain/Repository層で送出する。`index`は`children`/`confirmations`配列の一部でのみ発生したエラーの位置を示す（`docs/api.md` 0.3節）。
- FastAPIの`@app.exception_handler(AppError)`で`docs/api.md` 0.3節の共通形式`{ "error": { "code", "message", "index" } }`に変換する。
- 未捕捉例外は`500 INTERNAL_ERROR`にフォールバックし、詳細はログにのみ出力する（レスポンスに内部情報を含めない）。

## 7. Lambdaエントリポイント（`main.py`）

```python
from fastapi import FastAPI
from mangum import Mangum
from app.api.routers import public_checkin, auth, classes, schedule, pin, sessions, stats

app = FastAPI()
app.include_router(public_checkin.router)
app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(schedule.router)
app.include_router(pin.router)
app.include_router(sessions.router)
app.include_router(stats.router)

handler = Mangum(app)
```

## 8. 設定・環境変数（`core/config.py`）

| 変数 | 内容 |
|---|---|
| `DYNAMODB_TABLE_PREFIX` | テーブル名プレフィックス（環境分離なしのため固定値でも可） |
| `TEACHER_CODE_PARAM` | 指導者用8桁コードのSSMパラメータ名 |
| `ADMIN_CODE_PARAM` | 管理者用8桁コードのSSMパラメータ名 |
| `JWT_SECRET_PARAM` | JWT署名鍵のSSMパラメータ名 |
| `AWS_REGION` | Lambda実行リージョン |

SSMパラメータはLambdaのコールドスタート時に取得しモジュールレベルでキャッシュする（`REQUIREMENTS.md` 7.4節のコスト方針上、API呼び出しのたびに取得しない）。

## 9. ローカル開発

- Python 3.12（`REQUIREMENTS.md` 7.1節）。Lambdaランタイムもこれに合わせる。
- DynamoDB Local（Docker）またはmotoを使い、`repositories/dynamodb.py`のエンドポイントURLを環境変数で切り替える。
- テストは`pytest`（`REQUIREMENTS.md` 7.3節のCI方針と対応）。Domain層（`matching.py`・`reception_window.py`）は外部依存なしのユニットテストを重点的に書く。
