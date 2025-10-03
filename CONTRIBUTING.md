# 開発ガイドブック

Receipt Recipe プロジェクトのチーム開発ガイドです。

## � はじめに

### 必要なツール
- **Git**: バージョン管理
- **VS Code**: 推奨エディタ
- **GitHub アカウント**: ProjectTeam-Ramen組織メンバー

### 初回セットアップ
```bash
# プロジェクトをクローン
git clone https://github.com/ProjectTeam-Ramen/receipt-recipe.git
cd receipt-recipe

# 自分の名前を設定（初回のみ）
git config user.name "あなたの名前"
git config user.email "あなたのメール"
```

## 🔄 日常の作業フロー

### 作業開始時（毎回）
```bash
# 最新の状態に更新
git checkout main
git pull origin main

# 作業用ブランチを作成
git checkout -b feature/機能名
# 例: git checkout -b feature/user-login
```

### 作業中
```bash
# ファイルを編集後、変更を確認
git status
git diff

# 変更をコミット
git add .
git commit -m "feat: ログイン機能を追加"
```

### 作業完了時
```bash
# GitHubにアップロード
git push origin feature/機能名

# その後、GitHub上でプルリクエストを作成
```

## ⚡ よく使うGitコマンド

### 状況確認
```bash
git status           # 現在の状態を確認
git log --oneline    # コミット履歴を確認
git branch          # ブランチ一覧
```

### 変更の取り消し
```bash
git checkout .       # 未コミットの変更を取り消し
git reset HEAD~1     # 直前のコミットを取り消し（変更は保持）
```

### ブランチ操作
```bash
git checkout main           # mainブランチに移動
git checkout -b new-branch  # 新しいブランチを作成して移動
git branch -d branch-name   # ブランチを削除
```

## 📝 コミットメッセージのルール

### 基本形式
```
type: 日本語で簡潔な説明
```

### よく使うtype
- `feat`: 新機能を追加
- `fix`: バグを修正
- `docs`: ドキュメントを変更
- `style`: 見た目やフォーマットを変更
- `refactor`: コードの整理
- `test`: テストを追加・修正

### 良い例 ✅
```bash
git commit -m "feat: ユーザーログイン機能を追加"
git commit -m "fix: パスワードが保存されないバグを修正"
git commit -m "docs: READMEを更新"
git commit -m "style: インデントを統一"
```

### 悪い例 ❌
```bash
git commit -m "update"           # 何を更新したかわからない
git commit -m "ちょっと修正"       # typeがない
git commit -m "FIX: バグ修正"     # 大文字はNG
```

## � プルリクエスト（PR）の作り方

### 1. GitHub上でPRを作成
1. https://github.com/ProjectTeam-Ramen/receipt-recipe にアクセス
2. 「Compare & pull request」ボタンをクリック
3. タイトルと説明を入力
4. 「Create pull request」をクリック

### 2. PR のタイトル例
```
feat: ユーザー登録機能を追加
fix: ログイン時のエラーを修正
docs: 開発ガイドを更新
```

### 現在の状況
- 🔄 技術スタック検討中

## � 更新履歴

- **2025/10/03**: 初版作成
- プロジェクトの成長に合わせて随時更新予定