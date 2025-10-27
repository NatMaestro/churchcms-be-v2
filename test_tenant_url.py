import requests
import json

url = 'http://testchurch.lvh.me:8000/debug/tenant/'
print(f'\nTesting: {url}\n')

try:
    r = requests.get(url)
    print(f'Status: {r.status_code}')
    
    if r.status_code == 200:
        print('\n✅ Tenant detected!')
        print(json.dumps(r.json(), indent=2))
    else:
        print(f'\n❌ Error {r.status_code}')
        print(r.text[:500])
except Exception as e:
    print(f'\n❌ Request failed: {e}')

