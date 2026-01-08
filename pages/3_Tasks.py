import streamlit as st
import pandas as pd
from datetime import date
from lib.data_store import read_csv, write_csv

DATA_DIR = "data"

st.title("Tasks")

events = read_csv(f"{DATA_DIR}/events.csv")
tasks = read_csv(f"{DATA_DIR}/tasks.csv")

# ensure columns exist
for c in ["task_id","event_id","task_name","due_date","owner","status","notes"]:
    if c not in tasks.columns:
        tasks[c] = ""

event_id = st.selectbox("Event", events["event_id"].astype(str).tolist())

st.subheader("Add a task")
with st.form("add_task"):
    task_name = st.text_input("Task name")
    due = st.date_input("Due date", value=date.today())
    owner = st.text_input("Owner")
    status = st.selectbox("Status", ["Not started", "In progress", "Done", "Blocked"])
    notes = st.text_area("Notes", "")
    ok = st.form_submit_button("Add task")

if ok:
    max_id = pd.to_numeric(tasks["task_id"], errors="coerce").fillna(0).max()
    new_row = {
        "task_id": int(max_id) + 1,
        "event_id": event_id,
        "task_name": task_name,
        "due_date": due.isoformat(),
        "owner": owner,
        "status": status,
        "notes": notes
    }
    tasks = pd.concat([tasks, pd.DataFrame([new_row])], ignore_index=True)
    write_csv(f"{DATA_DIR}/tasks.csv", tasks, f"Add task: {event_id} #{int(max_id)+1}")
    st.success("Task added.")

st.subheader("Tasks for this event")
view = tasks[tasks["event_id"].astype(str) == str(event_id)].copy()
st.dataframe(view.sort_values(by=["due_date","status"], na_position="last"), use_container_width=True)
