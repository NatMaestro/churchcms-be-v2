"""
Run all tests for FaithFlow Backend
"""
import subprocess
import sys


def run_tests():
    """Run all tests using Django test runner"""
    print("="*60)
    print("🧪 RUNNING FAITHFLOW BACKEND TESTS")
    print("="*60 + "\n")
    
    # Run Django tests
    cmd = [
        sys.executable,
        'manage.py',
        'test',
        'tests',
        '--verbosity=2',
        '--keepdb',  # Keep test database for faster runs
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)


if __name__ == '__main__':
    run_tests()

