# AI数学教師 デプロイ手順書

## 現在の構成

```
ai-math-teacher/
├── main.py           ← FastAPI本体（CLIで編集禁止！）
├── system.py         ← システムプロンプト（CLIで編集禁止！）
├── templates/
│   └── index.html    ← チャットUI（CLIで編集禁止！）
├── requirements.txt
├── Dockerfile
└── .gitignore
```

> ⚠️ **ファイル編集はClaudeに作成してもらい、ダウンロード→上書きコピーで行う。PowerShellでの直接編集は文字化けの原因になるため禁止。**

---

## 現在の設定

| 項目 | 値 |
|------|-----|
| PROJECT_ID | ai-math-teacher-496804 |
| リージョン | asia-northeast1 |
| モデル | meta-llama/llama-4-scout-17b-16e-instruct |
| URL | https://ai-math-teacher-580790472489.asia-northeast1.run.app |
| ブランチ | master |

---

## ファイル変更の手順

1. Claudeにファイルを作成してもらう
2. ダウンロード
3. 上書きコピー：
```powershell
copy "$env:USERPROFILE\Downloads\ファイル名" "C:\Users\user\Documents\ai-math-teacher\ファイル名"
```
4. 確認（Pythonファイルの場合）：
```powershell
python "C:\Users\user\Documents\ai-math-teacher\main.py"
```

---

## デプロイコマンド（定番・1行）

```powershell
git add . ; git commit -m "変更内容" ; git push origin master ; docker build -t asia-northeast1-docker.pkg.dev/ai-math-teacher-496804/ai-math-teacher/app:latest . ; docker push asia-northeast1-docker.pkg.dev/ai-math-teacher-496804/ai-math-teacher/app:latest ; gcloud run deploy ai-math-teacher --image=asia-northeast1-docker.pkg.dev/ai-math-teacher-496804/ai-math-teacher/app:latest --region=asia-northeast1
```

---

## 環境変数（Cloud Run）

```powershell
gcloud run services update ai-math-teacher `
  --region=asia-northeast1 `
  --set-env-vars="MASTER_KEY=xxx,WHOP_API_KEY=xxx"
```

| 変数名 | 用途 |
|--------|------|
| MASTER_KEY | 開発用テストキー（Whop不要で入室可） |
| WHOP_API_KEY | Whopライセンス検証用APIキー |

---

## GCP初期設定（初回のみ）

```powershell
gcloud config set project ai-math-teacher-496804
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
gcloud artifacts repositories create ai-math-teacher --repository-format=docker --location=asia-northeast1
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

---

## Whop連携（未完成）

- [ ] Whopで商品作成（Type: Link）
- [ ] Cloud Run URLを設定
- [ ] Gating有効化
- [ ] WHOP_API_KEYを環境変数に設定済み

---

## コスト

- min-instances=0のためアクセスなしは**課金ゼロ**
- 無料枠: リクエスト200万回/月、CPU 180,000秒/月
- 小規模販売なら**月0円**で運用可能
