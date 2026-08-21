# Google sign-in

Research for [Google-based authentication](https://ticktick.com/webapp/#p/67076bd2657043bee4ed683a/tasks/6a7c960bebbd7d0001000200),
broken into [Offer Google sign-in alongside the email code](https://ticktick.com/webapp/#p/67076bd2657043bee4ed683a/tasks/6a886da18f0875d8ea2b3fa3).
Nothing here is built yet — this is the plan, the trade-offs, and the parts of our own
code that would move.

## The short version

Use **Google Identity Services (GIS) in ID-token mode**: Google renders the button, hands
the browser a signed ID token, we verify it on the backend and issue *our own* access and
refresh tokens exactly as `/auth/verify-code` already does.

Google **makes the email-code step optional — it does not replace it.** Both entry points
stay, both end at the same `User` row and the same session, and anyone who would rather not
put a Google account in the middle keeps the flow they have today.

`google-auth` is already in `requirements.txt` (it comes along for GCP), so the backend
needs no new dependency. The frontend needs no npm package either — GIS is a script tag.

## Which flow, and why not the others

| Flow | What you get back | Needs a client secret | Fits us |
| --- | --- | --- | --- |
| **GIS ID token** (`accounts.google.com/gsi/client`) | A signed JWT with `email`, `sub`, `name`, `picture` | No | **Yes** |
| Authorization Code + PKCE | A code you exchange for access/refresh tokens against Google APIs | No (PKCE) | Only if we ever call Google APIs |
| Server-side redirect (Authlib) | Same, via a backend round trip | Yes | No |

We want *identity*, not *access*. We never call Calendar, Drive or Gmail on the user's
behalf, so a Google access token would be issued and immediately thrown away. The ID token
is the whole answer, and it arrives without a redirect, without a client secret, and
without a callback route.

If a future task does want to read a user's Google Calendar into their day, that is the
code flow, and it is a **separate** login-independent authorization — don't pre-build it
here.

## Where it plugs into what we have

Today (`app/routers/auth.py`):

```
POST /auth/request-code   → Redis code + Resend email
POST /auth/verify-code    → find-or-create User → create_and_store_tokens → refresh cookie
                                                  ↓
                                          Msg[AuthResponse]
```

With Google — a *second* entry point, sitting beside the one above rather than over it:

```
Browser ──(1) click button──→ Google
        ←─(2) ID token (JWT)──┘
        ──(3) POST /auth/google { credential } ──→ FastAPI
                                                     (4) verify signature + aud + iss
                                                     (5) find-or-create User by email
                                                     (6) create_and_store_tokens  ← unchanged
                                                     (7) set refresh_token cookie ← unchanged
        ←────────── Msg[AuthResponse] ──────────────┘
```

Steps 6 and 7 are the existing code, called from a second entry point. Sessions,
`/auth/refresh`, `/auth/logout`, `/auth/sessions`, the `jti` blacklist and the
`CacheNamespace.users` cache all keep working untouched — they only ever knew about *our*
tokens, and they still only see our tokens.

`/auth/request-code` and `/auth/verify-code` are not deprecated by any of this and should
not be. Two routes, one session model.

## 1. Google Cloud Console

Same project as everything else (`GCP_PROJECT_ID`). One-time, in the console:

The console section is now called **Google Auth Platform**, with its own sidebar — Overview,
Branding, Audience, Clients, Data Access, Verification Center, Settings. The old single
"OAuth consent screen" page is split across Branding and Audience.

1. **Overview → Get started.** App name, support email, audience, contact email. Audience is
   **External** — Internal only exists for Workspace organizations.
2. **Branding.** App name, logo, home page, privacy policy and terms URLs, and the
   authorized domains the consent screen may link to (`memory-ful.com`). See *the logo
   question* below before uploading anything here.
3. **Data Access.** Scopes: `openid`, `email`, `profile`. All three are non-sensitive.
   Adding anything sensitive later (Calendar, Drive) is what pulls the app into Google's
   review process; that is the line not to cross casually.
4. **Clients → Create client → Web application.** Note: *Clients* means OAuth clients —
   client ID/secret pairs — not people who have signed in. Nothing in this console ever
   lists your users.
   - Authorized JavaScript origins: `http://localhost:3000`, `https://memory-ful.com`,
     `https://www.memory-ful.com`.
   - Authorized redirect URIs: **none needed** in ID-token mode. Leave empty.
5. Copy the client ID. It ends up in the frontend bundle and in the ID token's `aud` — it
   is public by design. The client *secret* on that page is for the code flow; we don't
   use it, so it never leaves the console.

Origins are matched exactly — scheme, host, port, no path, no trailing slash.

### Testing, publishing, and verification

Three separate things that are easy to conflate.

**Testing → In production** is a button on the **Audience** page. In Testing, only the
Google accounts listed there as test users can sign in at all, capped at 100. That cap —
not the 7-day grant expiry Google also mentions — is the real constraint for us: we never
hold a Google refresh token, so nothing of ours expires on that clock. Publishing lifts the
allow-list and lets any Google account in.

**Verification is a different gate, and non-sensitive scopes don't need it.** With only
`openid`/`email`/`profile` you can publish and take real users without a review.

**But uploading a logo triggers brand verification.** That review checks the app name, the
logo, the domain and the privacy-policy and terms URLs, and it takes days to weeks. So the
sequencing that avoids a rejected submission is:

1. Publish now, with **no logo**. Google sign-in works for everyone immediately.
2. Ship the privacy policy and terms pages.
3. *Then* upload the logo and let brand verification run against pages that actually exist.

Doing 3 before 2 is how you get a rejection and a second wait.

### The logo question

Whenever step 3 comes: Google wants a square image, 120×120 recommended, PNG/JPG/BMP. Of
what's in `memoryful-frontend/public/`:

| File | Size | Verdict |
| --- | --- | --- |
| `android-chrome-512x512.png` | 512×512, 414 KB | **Use this**, downscaled to 120×120 |
| `apple-touch-icon.png` | 180×180, 55 KB | Fine as-is if you'd rather not resize |
| `maskable-icon-512x512.png` | 512×512 | **No** — its art is inset for the maskable safe zone, so it renders small and lost inside Google's circle |
| `favicon.png` | 420×420 | Works, but it's the browser-tab asset; the chrome icon is the app mark |

### Privacy policy and terms

Two public pages on our own domain, `/privacy` and `/terms`. They are **frontend routes**,
not backend templates — `app/templates/` is for emails, and these have to open for a
stranger with no account. Filed as its own task; the content that matters is that day
content goes to OpenAI, Anthropic and Vertex, which is the most sensitive fact about this
app and has to be stated plainly.

## 2. Backend

### Settings

`google_client_id: str = ""` in `app/core/settings.py`, under a `# Google auth` heading.

It is **not** a secret: it does not go into `REQUIRED_SECRETS`, and therefore not into
Secret Manager. `GOOGLE_CLIENT_ID` lands in `.env.local` and `.env.prod` in the same pass,
per the root `CLAUDE.md`.

### Schema

`app/schemas/security.py`, next to `Token` and `AuthResponse`:

```python
class GoogleCredential(CamelModel):
    credential: str
```

### Verification helper

`app/core/security.py`:

```python
from fastapi.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

_GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


async def verify_google_id_token(credential: str) -> dict:
    # verify_oauth2_token fetches Google's signing certs over HTTPS with blocking I/O.
    def _verify() -> dict:
        return id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.google_client_id,
        )

    try:
        claims = await run_in_threadpool(_verify)
    except ValueError as e:
        raise HTTPException(401, "Invalid Google credential") from e

    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise HTTPException(401, "Invalid Google credential")

    if not claims.get("email_verified") or not claims.get("email"):
        raise HTTPException(403, "Google account has no verified email")

    return claims
```

The library checks the signature, `aud` and `exp`. The two checks above are ours: `iss`
because it costs a line, and `email_verified` because it is the *entire* basis for the
account linking below.

**Make the audience a list, not a single value.** `GOOGLE_CLIENT_IDS`, comma-separated,
parsed into a list and handed to `verify_oauth2_token` — google-auth's `jwt.decode` accepts
a list and checks membership. A native Android or iOS shell later needs its own OAuth
client, and its tokens can carry a different `aud`; as a list from day one that is an env
var edit instead of a code change. See *Surviving the mobile wrapper*.

### What's actually in `claims`

For `openid email profile`, the ID token carries:

| Claim | What it is | We use it |
| --- | --- | --- |
| `sub` | Stable Google account id, never reused | Yes — the `google_sub` task |
| `email`, `email_verified` | The address, and whether Google vouches for it | Yes — identity and linking |
| `given_name`, `family_name`, `name` | Display name parts | Yes — prefills the profile form |
| `picture` | Avatar URL | No — decided against |
| `locale` | e.g. `uk`, `en` | Not yet, but see below |
| `hd` | Workspace hosted domain | No — irrelevant to us |
| `iss`, `aud`, `azp`, `exp`, `iat`, `jti` | Token plumbing | Verified, not stored |
| `nonce` | Only if we send one | Phase two |

**There is no age, birthday, gender or phone number in there**, and that is not a privacy
choice we're making — Google simply doesn't put them in an ID token. Those live behind
extra People API scopes (`user.birthday.read` and friends) which are sensitive, would drag
us into the verification review, and we have no reason to request. So `age` stays what it
is today: a field the user fills in themselves, or leaves empty.

`locale` is the one unused claim worth remembering. The decided shape for i18n:

- **Unauthenticated** — the landing page follows `Accept-Language`. It's all we have, and
  it's a reasonable guess.
- **After a Google sign-in** — `locale` wins and the app switches to it. The user chose that
  in their Google account, so it beats a browser header.
- **After an email-code sign-in** — no signal exists, so it stays on the `Accept-Language`
  guess until the user picks a language in Settings.

Which means the Settings language field is needed regardless — it is the only lever the
email-code path ever gets, and it must also be able to override `locale` for someone whose
Google account language isn't the one they want to journal in.

### Endpoint

`app/routers/auth.py`, mirroring `verify_code` — the cookie block is copied verbatim,
which is the argument for pulling it into a small `_issue_session(db, user, request,
response)` helper that both endpoints call.

```python
@router.post("/google", response_model=Msg[AuthResponse])
async def google_sign_in(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    form: GoogleCredential,
) -> Msg[AuthResponse]:
    claims = await verify_google_id_token(form.credential)
    email = claims["email"].strip().lower()

    stmt = select(User).where(User.email == email)
    user: User | None = (await db.scalars(stmt)).one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        user = User(
            email=email,
            google_sub=claims["sub"],
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
        )
        db.add(user)
    elif not user.google_sub:
        user.google_sub = claims["sub"]

    await db.commit()
    await db.refresh(user)
    ...  # create_and_store_tokens + set_cookie, identical to verify_code
```

Three things worth stating out loud:

- **Linking is on the email, and that is safe here.** Our accounts have no password —
  ownership of the address is the only credential either path proves. The code flow proves
  it with a Redis code; Google proves it with `email_verified`. Someone who signs up by
  email and later clicks Google lands on the same row, which is what you want.

### When the Google account's email changes

`sub` is permanent; the email under it is not. Once `google_sub` exists, the lookup has to
run **`sub` first, email second** — the reverse order silently forks the account:

```python
user = await db.scalar(select(User).where(User.google_sub == claims["sub"]))

if user:
    if user.email != email:
        user.email = email  # Google is authoritative for this row's address
else:
    user = await db.scalar(select(User).where(User.email == email))
    ...  # link or create, as above
```

So yes — **the `email` column gets overwritten with whatever they authenticated with**, and
that is the right answer, because that column is also the address the login code is mailed
to. Leaving it stale would send codes to an address they no longer read.

Two things fall out of it:

- **`User.email` is unique, so the update can collide.** If the new Google address already
  belongs to a *different* local row, that's a real conflict — two accounts, one person,
  and no safe automatic merge. Answer it with a 409 and a message naming the problem, not
  an `IntegrityError` traceback.
- **Nothing else can change an email.** `update_me` takes `UserBase`, which has no `email`
  field — only `UserInDB` exposes it, and that's read-only. So Google is the only writer of
  that column, today and after this change.

**This is the actual cost of deferring `google_sub`,** and it's not zero — I said "costs
nothing" earlier and that was too strong. Until the column lands, lookup is email-only, so a
user who changes their Google address comes back as a brand-new account with an empty
journal. The reason it's still fine to defer: `@gmail.com` addresses can't be changed at
all, so this only reaches Workspace accounts and Google accounts backed by a non-Google
address, and the app has one user today. It's a real edge, just not an urgent one.
- **Ignore `claims["picture"]`.** Decided: users upload their own avatar, the way Telegram
  does. Beyond the product call, `User.photo` holds an S3/GCS *key* that `StorageService`
  presigns and `orphaned_keys` garbage-collects, so a `lh3.googleusercontent.com` URL in
  there would break presigning and could get "cleaned up".
- **Clear the user cache if you touch an existing row.** Backfilling `google_sub` or names
  on a returning user needs `await clear_cache(CacheNamespace.users, user.id)`, or
  `/auth/me` serves the pre-write row until the TTL lapses.

### Model change

```python
google_sub: Mapped[str | None] = mapped_column(unique=True, default=None)
```

Google's `sub` is the stable account id; the email can change under it. Storing it costs
one nullable column now and saves the account-recovery conversation later. Generate the
revision with `/migration` and let `migration-reviewer` look at it — a unique constraint on
a column added to a populated table is exactly the kind of DDL worth a second read.

**Deferred on purpose**, with a known cost: until it lands, a changed Google address comes
back as a second account. See *When the Google account's email changes*. Adding it later is
still cheap — a nullable column and one revision; existing rows get `NULL`, and Postgres
allows many `NULL`s under a unique constraint — but the lookup order in `/auth/google` has
to change with it, so the two land together.

### What does *not* change

- **No vite proxy edit.** `/auth/` is already in the regex in
  `memoryful-frontend/vite.config.ts`. This is a new route under an existing prefix, not a
  new top-level prefix.
- **No MCP tool.** `mcp_server/` mirrors read-only endpoints; a login POST has nothing to
  mirror.
- **No CORS change.** The SPA proxies to the API in dev and is same-origin in prod; the
  Google popup talks to Google, not to us.

## 3. Frontend

### Loading GIS

One script, `https://accounts.google.com/gsi/client`, loaded lazily from the auth view
rather than parked in `index.html` — the rest of the app has no use for it, and it is a
third-party request on every cold load if you put it in the head.

```ts
// src/composables/useGoogleIdentity.ts
let loading: Promise<void> | null = null

export function loadGoogleIdentity(): Promise<void> {
  loading ??= new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = 'https://accounts.google.com/gsi/client'
    el.async = true
    el.onload = () => resolve()
    el.onerror = () => reject(new Error('Failed to load Google Identity Services'))
    document.head.appendChild(el)
  })
  return loading
}
```

Then, in a `GoogleSignInButton.vue` mounted inside `WelcomeCard.vue`:

```ts
await loadGoogleIdentity()
window.google.accounts.id.initialize({
  client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
  callback: handleCredential,   // ({ credential }) => userStore.signInWithGoogle(credential)
  ux_mode: 'popup',
})
window.google.accounts.id.renderButton(buttonEl.value, {
  theme: 'filled_black',
  size: 'large',
  text: 'continue_with',
  shape: 'pill',
  width: Math.round(containerEl.value.clientWidth),
})
```

`VITE_GOOGLE_CLIENT_ID` goes in the frontend `.env.example` alongside
`VITE_API_BASE_URL`. Vite bakes it into the bundle at build time — fine, it's public.

### API and store

`src/api/auth.ts`:

```ts
signInWithGoogle(credential: string): Promise<ApiResponse<AuthResponse>> {
  return axios.post('/auth/google', { credential })
},
```

The store action is `verifyCode` with the first two lines swapped — same `setToken`, same
`fetchUserDetails`, same `[success, isNewUser]` return. `CodeVerification.vue`'s routing
rule (`isNewUser || !userStore.isProfileComplete → /login/details`) carries over unchanged,
and because we prefill `first_name` from the ID token, a Google user reaches that screen
with the name field already filled instead of empty.

Add `window.google.accounts.id.disableAutoSelect()` to `clearUser()`. Without it, Google
may silently re-sign the user in right after they log out.

### The placeholder row

This is the sibling task,
[replace several login options with a single "Google"](https://ticktick.com/webapp/#p/67076bd2657043bee4ed683a/tasks/6a7c6b4cebbd7d0001000215).
`WelcomeCard.vue` currently ends with:

```html
<p class="text-white/70">Or Sign In with</p>
<div class="flex gap-6 text-3xl">
  <font-awesome-icon :icon="['fab', 'google']" />
  <font-awesome-icon :icon="['fab', 'microsoft']" />
  <font-awesome-icon :icon="['fab', 'apple']" />
</div>
```

Three dead icons become one live button, and the copy becomes `Or sign in with`.

The email input and `Continue` button above it stay exactly where they are. "Or" is doing
real work in that sentence — the card offers two ways in, and the Google one is the second.

### Two things that will bite on mobile

- **`renderButton` draws into an iframe.** Tailwind classes don't reach inside it, `width`
  must be a **pixel number** (not `100%`), and Google caps it around 400px. In our
  full-width auth card that means measuring the container and re-rendering on resize —
  a `ResizeObserver` or a `useWindowSize` watcher. Check it at 375 before calling it done.
- **A phone on the LAN cannot sign in.** Google allows `http://` origins only for
  `localhost`. Testing on a real device at `http://192.168.x.x:3000` — which is how the
  mobile checks happen here — will fail the origin check. Worth knowing *before* an
  afternoon disappears into it. See below for why the Vercel preview isn't the way out.

### The Vercel preview looks like the answer and isn't

The dev branch auto-deploys to a stable per-branch host,
`memoryful-frontend-git-dev-vlad0307b-8854s-projects.vercel.app`. That *is* a real HTTPS
origin, it doesn't change per deploy, and registering it would make the button work on a
real phone.

But that build's `VITE_API_BASE_URL` is `https://api.memory-ful.com` — the **production**
API. Completing a sign-in there writes a real user row into production, which is off limits.
It would only ever prove the button renders, never that the flow works.

So the sign-in flow gets exercised at `localhost:3000` in a resized browser. Nothing about
it is touch-specific — it's a popup and a POST — so that is genuinely enough. If something
later turns out to need a device, the answer is an HTTPS tunnel in front of the local dev
server, not the preview deploy.

Also: if we ever set a `Cross-Origin-Opener-Policy` header on the app, use
`same-origin-allow-popups`. Plain `same-origin` severs the popup handle and the callback
never fires.

## Surviving the mobile wrapper

Worth settling now, because one of the wrapper options makes all of the above unusable.

**Google blocks OAuth inside plain embedded WebViews.** A hand-rolled Android `WebView`
shell — the shape you get from the Android Studio tutorial — is rejected with
`disallowed_useragent`, and the user cannot sign in with Google at all. It isn't degraded;
it's blocked, deliberately, because a WebView lets the host app read what the user types.

That does not sink the plan, but it does constrain the wrapper choice:

| Shell | Google sign-in |
| --- | --- |
| **TWA** (Trusted Web Activity) | **Works untouched** — it runs real Chrome, not a WebView. The manifest work already done is what unblocks this |
| Capacitor / React Native | Web flow blocked, but a native Google Sign-In plugin sidesteps it: the native SDK returns an ID token and `/auth/google` verifies it identically |
| Hand-rolled WebView | Dead end for Google sign-in |

The reason this stays cheap is that **the backend is the invariant**. Web GIS, Android
native, iOS native — every path ends with an ID token that `verify_oauth2_token` checks the
same way. What changes is only how the client obtains it, plus:

- an extra OAuth client per platform (Android needs the package name and SHA-1 fingerprint;
  iOS needs the bundle id), and
- the backend accepting **more than one audience**, which is why `GOOGLE_CLIENT_IDS` is a
  list from the start.

So nothing here becomes obsolete. Build the web flow now; the mobile shell reuses the
endpoint whichever way that decision goes.

## Security checklist

Everything the backend must not skip, in one place:

- `aud` equals our client ID — the library does it, but only if you actually pass the
  client ID in.
- `iss` is one of the two Google issuers.
- Signature and `exp` — the library.
- `email_verified` is `true`. This one is load-bearing: it is what makes email-based
  account linking safe.
- Never trust an email the *client* sends alongside the credential. Read it from the
  verified claims only.
- The response keeps the existing shape: refresh token in an `httponly` cookie, access
  token in the body. No new storage, no new surface.

### `localhost` as an authorized origin is not a hole

Worth spelling out, since both repos are public and the client ID ships in the bundle.

Anyone can clone the repo, run the frontend at `localhost:3000`, point
`VITE_API_BASE_URL` at production and click the Google button. What they get is **an account
of their own** — exactly what they'd get by visiting `memory-ful.com` and signing up. There
is no escalation, because identity is derived entirely from a claim set Google signed:

- An ID token can't be forged — it's signed by Google and we check the signature.
- A token can only be obtained for whoever actually consents in Google's popup, which is
  the attacker themselves. They cannot make Google mint one for your account.
- The client ID is not a credential. It names the app; it doesn't authorize anything.

The thing that *would* be a hole is the `TRUSTED_EMAILS` bypass, which skips code
verification entirely — and that's already gated: `Settings.trusted_emails` returns an empty
set whenever `environment != "development"`, so it cannot be reached in production no matter
what the env file says.

**Nonce** — GIS can carry a server-issued `nonce` (fetch it, stash it in Redis under a new
`RedisPrefix`, check-and-delete on verify). It defends against replay of a stolen token
within its ~1h validity. With HTTPS everywhere and an `aud` locked to our client ID the
residual risk is small, so this is a reasonable phase-2 item rather than a launch blocker
— but it *is* the difference between "correct" and "textbook correct".

**One Tap** (`google.accounts.id.prompt()`) is deliberately out of scope. It rides on
FedCM in Chrome and its behavior has been moving; the rendered button has none of that
churn. Ship the button, revisit One Tap once it's boring.

## Testing

`app/tests/test_auth.py` already has the fixtures. Monkeypatch the verifier — the point
under test is our branching, not Google's crypto:

```python
monkeypatch.setattr(
    "app.routers.auth.verify_google_id_token",
    lambda _: {"sub": "1", "email": email, "email_verified": True, "given_name": "Vlad"},
)
```

Cases worth having: new user is created and `is_new_user` is `True`; an existing
code-flow user is linked rather than duplicated (assert one row, and that `google_sub`
was filled); `email_verified: False` is rejected with 403; a garbage credential is 401;
the response sets the `refresh_token` cookie and the returned access token decodes with
`settings.access_secret_key`.

Manually, end to end: sign in with Google at 1280 and at 375, reload to confirm
`/auth/refresh` picks the session up, `/auth/sessions` lists it, and logout clears it and
does not auto-re-sign-in.

## Files that change

**memoryful-backend**

- `app/core/settings.py` — `google_client_id`
- `app/core/security.py` — `verify_google_id_token`
- `app/schemas/security.py` — `GoogleCredential` (+ export in `app/schemas/__init__.py`)
- `app/routers/auth.py` — `POST /auth/google`, and the extracted `_issue_session` helper
- `app/models/user.py` — `google_sub` + an Alembic revision
- `app/tests/test_auth.py` — the cases above
- `.env.local`, `.env.prod` — `GOOGLE_CLIENT_ID`

**memoryful-frontend**

- `src/api/auth.ts` — `signInWithGoogle`
- `src/stores/user.ts` — the store action, and `disableAutoSelect()` in `clearUser`
- `src/composables/useGoogleIdentity.ts` — script loader
- `src/components/auth/GoogleSignInButton.vue` — new
- `src/views/auth/WelcomeCard.vue` — the placeholder row
- `.env.example` — `VITE_GOOGLE_CLIENT_ID`

Both repos in one pass with mirrored messages, per the root `CLAUDE.md`.

## Decided

Settled 2026-08-21, and the reasons are worth keeping because each one looked like it could
go the other way:

- **`google_sub` waits**, but not for free. Linking on the verified email works without it,
  and adding it later is a nullable column plus one revision. The cost of the gap is that a
  changed Google address forks the account — bounded, because `@gmail.com` addresses cannot
  be changed at all.
- **Google owns the `email` column.** When the address under a `sub` changes, we overwrite
  ours, because that column is also where the login code gets mailed. Nothing else in the
  API can write it — `update_me` takes `UserBase`, which has no `email` field.
- **No Google avatar.** Users upload their own. Telegram doesn't import one either, and
  importing would drag `User.photo` out of the storage model it lives in.
- **The email-code flow stays.** Google is the second door, not the new one. This is the
  framing correction that renamed this whole document's premise — see *The short version*.
- **Mobile gets checked in a resized browser**, not on a device. The Vercel preview is a
  real HTTPS origin but talks to the production API, so signing in there is a production
  write. Full reasoning under *The Vercel preview looks like the answer and isn't*.

Local dev keeps the `TRUSTED_EMAILS` / `123123` bypass regardless. Real Google sign-in also
works at `http://localhost:3000` once the origin is registered, and creates a real row in
the restored local database.
