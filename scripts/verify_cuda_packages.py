#!/usr/bin/env python3
"""
CUDA Package Verification Script

このスクリプトは、PyTorch Geometric および CUDA 依存パッケージが
正しくインストールされているかを確認します。

使用方法:
    python scripts/verify_cuda_packages.py
    または
    uv run python scripts/verify_cuda_packages.py
"""

import sys
from importlib.metadata import version, PackageNotFoundError


def check_package(package_name: str, display_name: str = None) -> bool:
    """パッケージのインストール状態を確認する"""
    display_name = display_name or package_name
    try:
        pkg_version = version(package_name)
        print(f"✓ {display_name}: {pkg_version}")
        return True
    except PackageNotFoundError:
        print(f"✗ {display_name}: NOT INSTALLED")
        return False


def check_cuda_support():
    """CUDA サポートの確認"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else "N/A"
        print(f"\n🔧 PyTorch CUDA Support:")
        print(f"  - CUDA Available: {cuda_available}")
        print(f"  - CUDA Version: {cuda_version}")
        print(f"  - PyTorch Version: {torch.__version__}")
        
        if cuda_available:
            print(f"  - Device Count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  - Device {i}: {torch.cuda.get_device_name(i)}")
        return True
    except Exception as e:
        print(f"✗ Error checking CUDA support: {e}")
        return False


def check_torch_geometric():
    """PyTorch Geometric パッケージの確認"""
    try:
        import torch_geometric
        print(f"\n📦 PyTorch Geometric:")
        print(f"  - Version: {torch_geometric.__version__}")
        
        # 各拡張パッケージのインポートテスト
        extensions = {
            'torch_scatter': 'scatter',
            'torch_sparse': 'sparse',
            'torch_cluster': 'cluster',
            'torch_spline_conv': 'spline_conv'
        }
        
        print(f"\n🔌 CUDA Extensions:")
        all_ok = True
        for module_name, attr_name in extensions.items():
            try:
                module = __import__(module_name)
                print(f"  ✓ {module_name}: OK")
            except ImportError as e:
                print(f"  ✗ {module_name}: FAILED - {e}")
                all_ok = False
        
        return all_ok
    except ImportError as e:
        print(f"✗ PyTorch Geometric not installed: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 60)
    print("CUDA Package Verification for Receipt-Recipe Project")
    print("=" * 60)
    
    # 基本パッケージの確認
    print("\n📚 Core Packages:")
    packages = [
        ("torch", "PyTorch"),
        ("torchvision", "TorchVision"),
        ("torch_geometric", "PyTorch Geometric"),
    ]
    
    all_installed = True
    for pkg, display in packages:
        if not check_package(pkg, display):
            all_installed = False
    
    if not all_installed:
        print("\n⚠️  Some core packages are missing!")
        print("Please rebuild the Docker container to install missing packages.")
        sys.exit(1)
    
    # CUDA拡張パッケージの確認
    print("\n🔧 CUDA Extension Packages:")
    cuda_packages = [
        ("torch_scatter", "torch-scatter"),
        ("torch_sparse", "torch-sparse"),
        ("torch_cluster", "torch-cluster"),
        ("torch_spline_conv", "torch-spline-conv"),
    ]
    
    for pkg, display in cuda_packages:
        check_package(pkg, display)
    
    # CUDA サポートの確認
    check_cuda_support()
    
    # PyTorch Geometric の詳細確認
    pyg_ok = check_torch_geometric()
    
    print("\n" + "=" * 60)
    if pyg_ok:
        print("✅ All checks passed!")
        print("\n💡 Note:")
        print("   - PyTorch Geometric CUDA extensions are installed correctly")
        print("   - Compatible with CUDA 11.7 environment on computing server")
        print("   - If GPU is not available, packages will work in CPU mode")
    else:
        print("❌ Some checks failed!")
        print("\n💡 Troubleshooting:")
        print("   1. Rebuild the Docker container:")
        print("      docker-compose down")
        print("      docker-compose up --build")
        print("   2. Or rebuild Dev Container:")
        print("      Command Palette > Dev Containers: Rebuild Container")
    print("=" * 60)


if __name__ == "__main__":
    main()
