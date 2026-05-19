# 30分デプロイ手順書

## ファイル構成（これだけ）
```
ai-math-teacher/
├── main.py           ← FastAPI本体
├── system.py         ← システムプロンプト（ここだけ編集）
├── templates/
│   └── index.html    ← チャットUI
├── requirements.txt
├── Dockerfile
└── .gitignore
```

---

## ① ローカル確認（5分）

```bash
cd ai-math-teacher

# 仮想環境（任意）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# インストール
pip install -r requirements.txt

# 起動
uvicorn main:app --reload

# → http://localhost:8000 を開いてGroq APIキーを入力してテスト
```

---

## ② GitHub push（3分）

```bash
# 初回のみ
git init
git remote add origin https://github.com/YOUR_NAME/ai-math-teacher.git

# 毎回
git add .
git commit -m "initial commit"
git push origin main
```

---

## ③ GCP初期設定（初回のみ・10分）

```bash
# プロジェクトIDを設定
gcloud config set project YOUR_PROJECT_ID

# 必要なAPIを有効化
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# Artifact Registryリポジトリ作成（東京）
gcloud artifacts repositories create ai-math-teacher \
  --repository-format=docker \
  --location=asia-northeast1

# Docker認証
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

---

## ④ Cloud Runデプロイ（5分）

```bash
# イメージをビルド & プッシュ
docker build -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest .
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest

# デプロイ
gcloud run deploy ai-math-teacher \
  --image=asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1

# → デプロイ後にURLが表示される
# 例: https://ai-math-teacher-xxxx-an.a.run.app
```

---

## ⑤ Whopに登録（5分）

1. Whop → Product → Type: **Link**
2. URLに Cloud Run の URL を貼り付け
3. Gating 有効化 → 完了

---

## 更新デプロイ（次回から2コマンドだけ）

```bash
docker build -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest . && \
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest && \
gcloud run deploy ai-math-teacher \
  --image=asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/ai-math-teacher/app:latest \
  --region=asia-northeast1
```

---

## システムプロンプトの変更

`system.py` の `SYSTEM_PROMPT` を編集して再デプロイするだけ。  
ユーザーには一切見えません（サーバーサイドのみ）。

---

## コスト（ほぼ無料）

- min-instances=0 のため、アクセスがないときは**課金ゼロ**
- 無料枠: リクエスト200万回/月、CPU 180,000秒/月
- 小規模販売なら**月0円**で運用できます
