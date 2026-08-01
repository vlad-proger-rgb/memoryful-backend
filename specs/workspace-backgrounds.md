# Workspace & month backgrounds

How page backgrounds are stored, resolved and rendered.

## Who owns what

**The frontend owns the defaults.** Their URLs and blurred placeholders are
bundled constants in `memoryful-frontend/src/config/workspaceDefaults.ts`, so a
default background paints on the first frame with no network round trip — the
workspace store is seeded with them before the API answers.

**The backend never serves an unsigned URL.** `GET /workspaces/me` returns a
`backgrounds` map holding only the pages the user has customized. Every key in it
is `users/<id>/…` — private, and therefore presigned. The client fills the gaps
from `DEFAULT_BACKGROUNDS`.

So "default" means "no row", and the backend's only job is signing the keys that
do exist.

## Storage

`workspace_backgrounds` holds one row per customized page:

| column | meaning |
| --- | --- |
| `user_id` + `page` | composite primary key |
| `object_key` | key in the private bucket |
| `placeholder` | blurred preview; null if generation failed |

`page` is plain text rather than a DB enum, so adding a page needs no migration.
`WorkspacePage` validates it at the API boundary instead.

The row stores the key and placeholder; the router adds `url` and `isVideo` on
read. Either way one page is one object — the row, the API entry and the store
entry all describe a single background, rather than splitting it across parallel
per-page structures.

## Reading and writing

`GET /workspaces/me`:

```json
{ "backgrounds": { "day": { "key": "users/…/a.png", "url": "https://…",
                            "isVideo": false, "placeholder": "data:image/webp;base64,…" } } }
```

`PUT /workspaces/me` touches only the pages present in the body. `key: null`
clears a page back to its default:

```json
{ "backgrounds": { "day": { "key": "users/…/b.png", "placeholder": "data:…" },
                   "search": { "key": null } } }
```

## Replaced media

Every upload mints a fresh `uuid4` prefix, so an object key is referenced by at
most one row, ever. Replacing a background therefore leaves the previous object
provably unreferenced, and the write that orphaned it deletes it.

This runs for workspace backgrounds, month backgrounds, day photos and avatars
via `StorageService.delete_objects`, always **after** the commit — deleting
first would destroy a live object if the commit then failed.

It is dispatched as a `BackgroundTasks` job, not awaited in the handler, and the
blocking boto3 call runs on a worker thread. Both matter: deleting a large object
took **tens of seconds** against local MinIO, which otherwise held the response
open (so the UI couldn't refresh) and stalled the whole event loop meanwhile.

Best-effort by design: a storage error is logged and swallowed, since the user's
write already succeeded.

Two traps the diff has to avoid, both handled by `orphaned_keys`:

- **An unsent field keeps its value.** A PUT carrying only `description` must not
  read the absent `background_image` as "cleared".
- **Fields can share a key.** A day's `main_image` and `images` may point at the
  same object, so they are differenced together rather than separately.

Objects uploaded but never saved — the tab closed between the presigned PUT and
the save — have no row to trigger this, and still need a sweep to collect. None
exists yet.

## Pages

One per view: `dashboard`, `day`, `month`, `search`, `settings`. Defined twice,
once per language — `WorkspacePage` (backend, also validating the upload intent's
page key) and `WORKSPACE_PAGES` in `types/workspace.ts` (frontend, with
`WorkspacePageKey` derived from it).

Adding one means: both lists, a `DEFAULT_BACKGROUNDS` entry, a label in
`WorkspaceSettings.vue`, and the asset in the public bucket. No migration.

The month view resolves in two steps: a month with its own `background_image`
wins, otherwise the `month` page background applies. Per-month art is an override
on top of the page setting, not a competing mechanism.

## Buckets

Public assets live in **`memoryful-public`**, separate from user data.

`memoryful` (private) keeps public access prevention enforced — it holds every
user's photos, and PAP is what stops a mis-scoped IAM change from exposing them.
`allUsers` bindings are rejected there by design, which is why public assets
needed their own bucket rather than a public prefix in the existing one.

Everything in `memoryful-public` is meant to be public, so it needs no IAM
condition:

```bash
gcloud storage buckets create gs://memoryful-public --location=eu --uniform-bucket-level-access --no-public-access-prevention
```

```bash
gcloud storage buckets add-iam-policy-binding gs://memoryful-public --member=allUsers --role=roles/storage.objectViewer
```

Point the frontend at it with `VITE_PUBLIC_ASSET_BASE_URL`.

## Local setup

`bucket_base/` is gitignored — binaries with no reason to sit in the repo. Pull
them from the public bucket when setting up a machine:

```bash
gcloud storage rsync -r gs://memoryful-public/users/defaults memoryful-backend/bucket_base/users/defaults
```

`minio-init` then mirrors `bucket_base/` into local MinIO on every
`docker compose up`. Dev keeps public and private assets in that one
anonymous-download bucket, so the built-in `VITE_PUBLIC_ASSET_BASE_URL` fallback
works with no config; only the base URL differs between environments.

Publishing a change goes the other way:

```bash
gcloud storage rsync -r memoryful-backend/bucket_base/users/defaults gs://memoryful-public/users/defaults
```

## Asset encoding

Images are WebP at 1920px; the search video is H.264 CRF 32 with audio stripped.

`+faststart` is **not optional**. It moves the `moov` atom ahead of `mdat` so the
browser can render the first frame after a few hundred KB instead of downloading
the whole file — without it a 53 MB clip left the page blank for 5-10 seconds.

```bash
ffmpeg -i in.jpg -vf scale=1920:-2 -c:v libwebp -quality 80 -compression_level 6 out.webp
ffmpeg -i in.mp4 -c:v libx264 -crf 32 -preset slow -pix_fmt yuv420p -movflags +faststart -an out.mp4
```

CRF 32 is a deliberate trade for a backdrop that gets dimmed behind UI. The curve
is flat here — CRF 30 costs ~65% more bytes for a negligible gain.

**Replacing an asset:** URLs carry a long `immutable` cache header, so
overwriting a key in place can leave stale copies in browser caches. Give the
replacement a new filename and update `workspaceDefaults.ts`.

## Blurred placeholders (LQIP)

A ~32px WebP `data:` URI that paints blurred while the real media loads. A few
hundred bytes, carried inside a response the client already makes, so it costs no
extra request.

- **Defaults** — constants in `workspaceDefaults.ts`. Regenerate alongside the
  asset; a stale one flashes the wrong colours.

  ```bash
  ffmpeg -i <source> -vf scale=32:-2 -c:v libwebp -quality 55 -compression_level 6 lqip.webp && base64 -w0 lqip.webp
  ```

- **Uploads** — generated in the browser by `useMediaPlaceholder` (canvas
  downscale; for video it seeks past zero and captures the first frame), then sent
  with the record. Stored in `months.background_placeholder` or
  `workspace_backgrounds.placeholder`.

## Rendering

`MediaBackground` paints a permanent dark base, then mounts one
`MediaBackgroundLayer` on top. When `src` changes the incoming layer mounts over
the outgoing one and the two cross-fade.

Two layers rather than one because a reused `<img>` keeps painting its previous
bitmap until the new `src` decodes — animating a single element's opacity can
only dip and pop back, never fade *between* two images. Each layer owns its load
state, so the outgoing one isn't reset by the incoming one's events.

A `src` change waits up to `DECODE_GRACE_MS` for the new image to decode before
swapping. Revisiting a cached background therefore cross-fades sharp-to-sharp;
past the grace period it swaps anyway and lets the new layer's blur cover the wait.
