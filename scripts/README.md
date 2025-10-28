# Scripts

このディレクトリには、開発・運用に役立つユーティリティスクリプトが含まれています。

## 利用可能なスクリプト

### verify_cuda_packages.py

PyTorch Geometric および CUDA 依存パッケージが正しくインストールされているかを確認するスクリプトです。

**使用方法:**
```bash
# Dev Container内で実行
uv run python scripts/verify_cuda_packages.py

# または直接実行
python scripts/verify_cuda_packages.py
```

**確認項目:**
- PyTorch のインストール状態
- PyTorch Geometric のインストール状態
- CUDA 拡張パッケージ (torch-scatter, torch-sparse, torch-cluster, torch-spline-conv)
- CUDA デバイスの利用可能性
- GPU 情報（利用可能な場合）

**使用例:**
```bash
# 正常にインストールされている場合
$ uv run python scripts/verify_cuda_packages.py
============================================================
CUDA Package Verification for Receipt-Recipe Project
============================================================

📚 Core Packages:
✓ PyTorch: 1.12.0
✓ TorchVision: 0.13.0
✓ PyTorch Geometric: 2.3.1

🔧 CUDA Extension Packages:
✓ torch-scatter: 2.1.1+pt112cu117
✓ torch-sparse: 0.6.17+pt112cu117
✓ torch-cluster: 1.6.1+pt112cu117
✓ torch-spline-conv: 1.2.2+pt112cu117

🔧 PyTorch CUDA Support:
  - CUDA Available: True
  - CUDA Version: 11.7
  - PyTorch Version: 1.12.0
  - Device Count: 1
  - Device 0: NVIDIA GeForce RTX 3080

📦 PyTorch Geometric:
  - Version: 2.3.1

🔌 CUDA Extensions:
  ✓ torch_scatter: OK
  ✓ torch_sparse: OK
  ✓ torch_cluster: OK
  ✓ torch_spline_conv: OK

============================================================
✅ All checks passed!

💡 Note:
   - PyTorch Geometric CUDA extensions are installed correctly
   - Compatible with CUDA 11.7 environment on computing server
   - If GPU is not available, packages will work in CPU mode
============================================================
```

## スクリプトの追加

新しいスクリプトを追加する場合は、以下のガイドラインに従ってください:

1. **実行権限**: `chmod +x scripts/your_script.py` で実行可能にする
2. **Shebang**: `#!/usr/bin/env python3` をファイルの先頭に追加
3. **ドキュメント**: このREADMEに使用方法を追加
4. **エラーハンドリング**: 適切なエラーメッセージを表示
5. **日本語サポート**: 必要に応じて日本語メッセージを含める
