# Deploying to a public website (Streamlit Community Cloud)

This puts your dashboard online at a URL like `https://<you>-stocks.streamlit.app`,
free, public. Your code is already committed to a local git repo — you just need to
push it to GitHub and connect Streamlit Cloud. ~5 minutes.

> Reminder of the cloud trade-offs (see chat): the live table + **Refresh** button
> work online, but the **history chart resets** on restarts and the **daily
> scheduler does not run** on the cloud free tier. Keep `run_dashboard.bat` /
> `run_scheduler.bat` locally for those.

---

## Step 1 — Create a GitHub account (skip if you have one)
Go to https://github.com/signup and make a free account.

## Step 2 — Create an empty repository
1. Go to https://github.com/new
2. **Repository name:** `stock-watchlist` (anything is fine)
3. **Public** (required for the free Streamlit tier)
4. Do **NOT** tick "Add a README / .gitignore / license" — leave it empty.
5. Click **Create repository**.
6. On the next page, copy the URL under "…or push an existing repository",
   it looks like: `https://github.com/YOURNAME/stock-watchlist.git`

## Step 3 — Push your code (tell me when you've done Step 2)
Run these in the project folder, replacing the URL with yours. **I can run these
for you** once you give me the repo URL — just paste it in chat. Otherwise, in a
terminal:

```bash
cd "C:/Users/RohitAgrawal/Downloads/Claude code/Screener scrapper"
git remote add origin https://github.com/YOURNAME/stock-watchlist.git
git branch -M main
git push -u origin main
```

The first `git push` will pop a GitHub login window in your browser — sign in once
and it remembers you.

## Step 4 — Deploy on Streamlit Cloud
1. Go to https://share.streamlit.io and click **Sign in with GitHub** (authorize it).
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `YOURNAME/stock-watchlist`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. (Optional but recommended) Click **Advanced settings** → set **Python version**
   to **3.12** (Streamlit Cloud doesn't support 3.14 yet; 3.12 works fine here).
5. Click **Deploy**. First build takes ~2–3 minutes while it installs the packages.

When it finishes you get your public URL. Bookmark it — that's your live dashboard.

## Step 5 — Updating it later
Any time you change the code or watchlist locally:
```bash
git add -A
git commit -m "update watchlist"
git push
```
Streamlit Cloud auto-redeploys within a minute.

---

### Notes
- The app **auto-fetches data on first visit**, so the page won't be blank.
- `config.json` (your watchlist) is committed and therefore public. Don't put
  anything private in it.
- `stocks.db` is intentionally **not** pushed (it's runtime data and would go stale).
