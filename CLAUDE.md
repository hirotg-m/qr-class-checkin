# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

QR コードを使ったスポーツ教室の会員・出欠管理システム。1つの団体が複数のクラスを運営し、クラスごとに参加者を明確に区別して記録することを目的とする。保護者は QR コード経由でログイン不要の参加登録フォームを使い、指導者・運営者は認証付き画面で参加状況を確認する。詳細な要件は `REQUIREMENTS.md` を参照(機能要件・データ設計・API 設計・認証方式・コスト方針まで網羅したドラフト)。

**現状**：実装コードはまだ存在しない。リポジトリには `REQUIREMENTS.md` / `README.md` / `LICENSE` のみがある段階。`/frontend`, `/backend`, `/infra` 等が実装され次第、このファイルにビルド／テスト／lint コマンドを追記すること。

## スコープ

中心機能はクラスごとの QR 自己受付による参加登録(`REQUIREMENTS.md` 3節)。

含む機能：
- クラス管理（クラスは複数登録可能。クラスごとにクラス名・対象学年・スケジュール・月次 PIN・参加者名簿・参加記録を分けて持つ。管理者は管理画面からクラス・活動予定・月次 PIN の追加・編集・削除が可能な CRUD UI を持つ）
- 対象学年設定（クラスごとに参加可能な学年を設定。例：クラスAは小学生のみ、クラスBは小学5・6年のみ、クラスCは小学生・中学生）
- 活動予定管理（`Schedule`、クラスごと。管理者が管理画面から編集）
- 月次 PIN 管理（`MonthlyPin`、クラスごと。管理者が管理画面から編集）
- 保護者 QR 自己登録フォーム（学年・氏名＋ PIN、ログイン不要、事前登録不要。学年はクラスの対象学年の範囲内から選択）
- 受付時間の自動判定（活動開始30分前〜終了時刻。`Schedule` の時刻から自動判定、手動 ON/OFF は実装しない）
- 参加者照合（クラスごとの `Participants` と氏名・学年で照合、新規/既存判定、表記ゆれ時は候補提示）
- 指導者代理入力（フォールバック。`inputBy` で本人／代理を区別）
- 参加履歴閲覧（運営者向け：クラスごとの日別参加者一覧、参加者ごとの参加回数、学年別参加人数推移グラフ）

現時点でスコープ外（`REQUIREMENTS.md` 6節）：
- 会費管理・会員名簿管理
- 活動内容記録・写真・実績報告書出力

## アーキテクチャ（計画）

```text
[S3 + CloudFront]  静的ホスティング（管理画面フロント：React, Node.js 22）
        ↓
[API Gateway]      HTTP API
        ↓
[Lambda]           FastAPI + Mangum アダプタ（Python 3.12）
        ↓
[DynamoDB]         データ永続化（オンデマンド課金）
```

- 保護者向け QR 登録フォームも指導者向け管理画面も同じ API Gateway/Lambda 経由で DynamoDB に読み書きする。保護者側はログイン不要。
- インフラ構築は AWS SAM（`/infra/template.yaml`、`sam deploy`で初回・変更時に手動実行）。CI/CD はコードデプロイのみを対象とし、インフラ変更（テーブル追加・権限変更等）は含めない。
- 環境分離（dev/prod）は行わない。独自ドメインも使用しない（コスト抑制のため。目標：月額300円以下）。

### 想定リポジトリ構成
```text
/frontend        React
/backend         FastAPI + Lambda ハンドラ（Mangum）
/infra
  template.yaml         SAM テンプレート（初回・変更時に `sam deploy` で手動実行）
/.github/workflows
  ci.yml        PR時：lint・テスト（デプロイなし）
  deploy.yml    main push時：バックエンド・フロントエンドのコードデプロイのみ
```

## 認証方式（重要な設計判断）

- 個人アカウントは持たず、2種類の共通コードでログイン（それぞれ定期的に変更する運用）。
  - 指導者用8桁数字コード：権限は閲覧のみ（書き込み系エンドポイントは含まない。参加者の代理入力のみ例外で指導者コードでも可）
  - 管理者用8桁数字コード：閲覧に加えデータの編集が可能
- コードと JWT 署名鍵はどちらも AWS SSM Parameter Store（SecureString）で管理し、コード内やログに平文を残さない。
- ログイン試行はレート制限（同一IPから3分間に10回失敗で一時ロック、DynamoDB に失敗回数を記録し TTL で自動クリア）。
- JWT の有効期限は8時間。ペイロードは最小限（`role: viewer` または `role: admin`, `exp` 程度、個人アカウントがないため `sub` は固定値または省略）。

## データ設計（DynamoDB）

クラス(`classId`)を軸に全テーブルをスコープする。同一人物が複数クラスに参加する場合もクラスごとに別レコードとして扱い、クラスごとの参加者を明確に区別する。

| テーブル | PK | SK | 主な属性 |
|---|---|---|---|
| `Classes` | `CLASS#<classId>` | - | クラス名、説明、対象学年（配列） |
| `Schedule` | `CLASS#<classId>` | `DATE#<date>` | 開始時刻、終了時刻、会場 |
| `MonthlyPin` | `CLASS#<classId>#MONTH#<yyyy-mm>` | - | 月ごとの暗証番号 |
| `Participants` | `CLASS#<classId>` | `PARTICIPANT#<id>` | 氏名、学年、初回参加日 |
| `SessionLog` | `CLASS#<classId>#DATE#<date>` | `PARTICIPANT#<id>` | 新規/既存フラグ、来場時刻、`inputBy`（本人/代理） |

会員情報を扱うため、開発中のリポジトリはプライベート推奨。OSS 公開する場合は `REQUIREMENTS.md` のような匿名化版を別途用意する。

## 未決事項

- 参加記録には連絡先が紐づかない。緊急連絡手段の確保方法は別途検討（`REQUIREMENTS.md` 5節）。
- 指導者ログインコードの更新頻度（月次／年度ごと等、`REQUIREMENTS.md` 8.5節）。
