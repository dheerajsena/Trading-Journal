import os, io, time
import streamlit as st
from github import Github

def maybe_sync_csv_to_github(storage):
    # Only sync if using CSV backend
    if getattr(storage, "backend", "sqlite") != "csv":
        return
    token = st.secrets.get("github", {}).get("token", "")
    repo_name = st.secrets.get("github", {}).get("repo", "")
    branch = st.secrets.get("github", {}).get("branch", "main")
    if not token or not repo_name:
        return  # not configured
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        path = "data/trades.csv"
        # Read the local CSV
        with open("data/trades.csv", "rb") as f:
            content = f.read()
        message = f"Update trades.csv at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            file = repo.get_contents(path, ref=branch)
            repo.update_file(path, message, content.decode("utf-8"), file.sha, branch=branch)
        except Exception:
            # create if not exists
            repo.create_file(path, message, content.decode("utf-8"), branch=branch)
        st.info("CSV synced to GitHub repo.")
    except Exception as e:
        st.warning(f"GitHub sync skipped: {e}")
