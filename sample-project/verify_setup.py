#!/usr/bin/env python3
"""
Verification script to test the sample project setup.

This script verifies that all components work correctly before
pushing to the DevOps pipeline.
"""

import subprocess
import sys
import os
import requests
import time
import json
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description} - EXISTS")
        return True
    else:
        print(f"❌ {description} - MISSING")
        return False


def test_api_endpoints():
    """Test API endpoints if the server is running."""
    base_url = "http://localhost:5000"
    endpoints = [
        ("/", "Home endpoint"),
        ("/health", "Health endpoint"),
        ("/info", "Info endpoint")
    ]
    
    print("\n🌐 Testing API endpoints...")
    
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description} - OK (Status: {response.status_code})")
            else:
                print(f"❌ {description} - FAILED (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  {description} - Cannot connect (Server not running)")
    
    # Test POST endpoint
    try:
        payload = {"operation": "add", "num1": 5, "num2": 3}
        response = requests.post(f"{base_url}/calculate", 
                               json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('result') == 8:
                print("✅ Calculate endpoint - OK")
            else:
                print("❌ Calculate endpoint - Wrong result")
        else:
            print(f"❌ Calculate endpoint - FAILED (Status: {response.status_code})")
    except requests.exceptions.RequestException:
        print("⚠️  Calculate endpoint - Cannot connect (Server not running)")


def main():
    """Main verification function."""
    print("🚀 DevOps Pipeline Demo - Project Verification")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Please run this script from the sample-project directory")
        sys.exit(1)
    
    # File existence checks
    required_files = [
        ("app.py", "Main application file"),
        ("utils.py", "Utility functions file"),
        ("test_app.py", "Application tests"),
        ("test_utils.py", "Utility tests"),
        ("requirements.txt", "Requirements file"),
        ("Dockerfile", "Docker configuration"),
        (".env.example", "Environment template"),
        ("README.md", "Documentation"),
        (".gitignore", "Git ignore file")
    ]
    
    print("\n📁 Checking required files...")
    files_ok = all(check_file_exists(file, desc) for file, desc in required_files)
    
    # Code quality checks
    print("\n🔍 Running code quality checks...")
    
    # Install dependencies first
    install_ok = run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                           "Installing dependencies")
    
    if install_ok:
        # Run linting
        lint_ok = run_command([sys.executable, "-m", "pylint", "--errors-only", "app.py", "utils.py"],
                            "Linting Python files")
        
        # Run tests
        test_ok = run_command([sys.executable, "-m", "pytest", "-v"],
                            "Running test suite")
        
        # Test coverage
        coverage_ok = run_command([sys.executable, "-m", "pytest", "--cov=.", "--cov-report=term-missing"],
                                "Testing with coverage")
        
        # Docker build test
        docker_ok = run_command(["docker", "build", "-t", "devops-demo-test", "."],
                              "Building Docker image")
    else:
        lint_ok = test_ok = coverage_ok = docker_ok = False
    
    # API tests (optional - only if server is running)
    test_api_endpoints()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    checks = [
        ("Required files", files_ok),
        ("Dependencies", install_ok),
        ("Code linting", lint_ok),
        ("Test suite", test_ok),
        ("Test coverage", coverage_ok),
        ("Docker build", docker_ok)
    ]
    
    all_passed = True
    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")
        if not status:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! Your project is ready for the DevOps pipeline.")
        print("\nNext steps:")
        print("1. Initialize git repository: git init")
        print("2. Add files: git add .")
        print("3. Commit: git commit -m 'Initial commit'")
        print("4. Push to your repository")
        print("5. Configure webhook to trigger the DevOps pipeline")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
