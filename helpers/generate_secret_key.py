"""
Generate a secure SECRET_KEY for production
"""
from django.core.management.utils import get_random_secret_key

print("\n" + "="*60)
print("🔐 PRODUCTION SECRET KEY")
print("="*60)
print("\nYour secure SECRET_KEY for production:\n")
print(get_random_secret_key())
print("\n" + "="*60)
print("\n💡 Copy this and add it to Render environment variables:")
print("   SECRET_KEY=<paste-the-key-above>")
print("\n⚠️  IMPORTANT: Keep this secret! Don't commit it to Git!")
print("\n")




