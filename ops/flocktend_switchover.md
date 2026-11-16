# Switching from faithflow360.com to flocktend.com

The code accepts both domains, so it can ship before the switch. The switch
itself is settings and DNS only, done in the order below.

**Sign-in note.** Sign-in cookies belong to one domain (`COOKIE_DOMAIN`).
On switch-over day everyone has to sign in once more. No data changes.

Placeholders used below:
- `<distribution>.cloudfront.net` is the CloudFront address of the website.
- `<render-address>` is the address Render gives you when you add a custom domain.

---

## Part A: prepare (any day; users notice nothing)

### A1. AWS certificate, in **us-east-1 (N. Virginia)**

CloudFront takes only one certificate, so it must cover both domains.

1. Open AWS Certificate Manager and select region **us-east-1**.
2. Request a public certificate with these 4 names:
   - `flocktend.com`
   - `*.flocktend.com`
   - `faithflow360.com`
   - `*.faithflow360.com`
3. Choose DNS validation.
4. Add the CNAME records it shows at each domain's DNS provider.
5. Wait until the status says **Issued**.

### A2. DNS for flocktend.com, at the place you bought it

| Name | Type | Points to |
|---|---|---|
| `*` (wildcard: every church, and www) | CNAME | `<distribution>.cloudfront.net` |
| `@` (flocktend.com itself) | ALIAS / ANAME / flattened CNAME | `<distribution>.cloudfront.net` |
| `api` | CNAME | `<render-address>` (from step A4) |

- `api` has its own record, so it is not caught by the wildcard.
- If your provider cannot point `@` at CloudFront, move the domain's DNS to Cloudflare (free), which can.

### A3. CloudFront

1. Open the website distribution and choose **Edit**.
2. Under **Alternate domain names**, add `flocktend.com` and `*.flocktend.com`. Keep the faithflow360 names.
3. Under **Custom SSL certificate**, pick the new certificate from A1.
4. Save.

### A4. Render (backend)

1. In Settings → Custom Domains, add `api.flocktend.com`. Keep `api.faithflow360.com`.
2. Render shows the address for the `api` DNS record. Add it as in A2.
3. Wait for the certificate to say **Verified**.

### A5. Resend (email)

1. Add the domain `flocktend.com`.
2. Add the DNS records it shows: SPF, DKIM and MX on its send subdomain.
3. Wait for **Verified**.

### A6. Check before going on

Each of these should work over HTTPS:
- `https://flocktend.com`. It shows the landing page.
- `https://api.flocktend.com/health/`.
- Resend shows `flocktend.com` as verified.

---

## Part B: switch-over (one sitting, about 30 minutes)

### B1. Render environment variables

Variables set in the Render dashboard override the code's defaults. Change these:

| Variable | New value |
|---|---|
| `FRONTEND_URL` | `https://www.flocktend.com` |
| `COOKIE_DOMAIN` | `.flocktend.com` |
| `DEFAULT_FROM_EMAIL` | `noreply@flocktend.com` (or a sender name, e.g. `Flocktend <noreply@flocktend.com>`) |
| `ALLOWED_HOSTS` | `.onrender.com,.flocktend.com,.faithflow360.com` |
| `CORS_ALLOWED_ORIGINS` (only if it is set) | add `https://flocktend.com,https://www.flocktend.com` |
| `CSRF_TRUSTED_ORIGINS` (only if it is set) | add `https://flocktend.com,https://www.flocktend.com` |

Leave `PLATFORM_DOMAIN` unset; it defaults to `flocktend.com`.

### B2. GitHub secret for the website

In the faithflow-studio repo, go to Settings → Secrets → Actions. Set `VITE_API_URL` to `https://api.flocktend.com/api/v1`.

### B3. Release

1. Merge `develop` into `main` in **both** repos. The backend deploys on Render; the website deploys through GitHub Actions to S3 and CloudFront.
2. Wait for both deploys to finish.

### B4. Paystack (only when online payment is switched on)

In the Paystack dashboard, set the webhook URL to:
`https://api.flocktend.com/api/v1/churches/subscription-payment/webhook/`

### B5. Redirect the old domain

1. In CloudFront → Functions, create a function named `redirect-old-domain`. Use this code:

```js
function handler(event) {
  var request = event.request;
  var host = request.headers.host.value;
  var OLD = 'faithflow360.com';
  if (host === OLD || host.endsWith('.' + OLD)) {
    var query = Object.keys(request.querystring).map(function (k) {
      var v = request.querystring[k];
      return v.value ? k + '=' + v.value : k;
    }).join('&');
    var url = 'https://' + host.slice(0, host.length - OLD.length) + 'flocktend.com'
      + request.uri + (query ? '?' + query : '');
    return { statusCode: 301, statusDescription: 'Moved Permanently',
             headers: { location: { value: url } } };
  }
  return request;
}
```

2. Publish the function.
3. Attach it to the distribution's default behaviour as a **Viewer request** function.

The API (`api.faithflow360.com`) is not redirected. It keeps answering until you remove it in Part C.

### B6. Check

- Open `https://olamchurch.faithflow360.com/login`. It should land on `https://olamchurch.flocktend.com/login`.
- Sign in there.
- Request a password reset. The email should come from `noreply@flocktend.com`, and the link should start with `https://olamchurch.flocktend.com`.
- In the platform admin, create a test church. Its address should end in `.flocktend.com`.

---

## Rollback

The code accepts both domains, so rolling back is settings only:
1. Put the old values back in B1 and B2.
2. Redeploy the website.
3. Detach the B5 function.

---

## Part C: later (after about 3 months)

1. Set the Render variable `LEGACY_PLATFORM_DOMAINS` to empty. faithflow360.com is then no longer trusted for sign-in requests. The redirect keeps working because it runs in CloudFront.
2. Remove `api.faithflow360.com` from Render's custom domains.
3. Keep `faithflow360.com` registered for at least a year, so old links and emails keep redirecting.
