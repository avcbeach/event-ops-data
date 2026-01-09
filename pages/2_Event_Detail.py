import pandas as pd
import streamlit as st
from datetime import date, datetime

from lib.data_store import read_csv, write_csv

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]

today = date.today()

# --------------------------------------------------
# HELPERS (SHARED LOGIC)
# --------------------------------------------------
def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except:
        return None

def update_task(task_id, updates: dict):
    base = read_csv("data/tasks.csv", TASK_COLS)
    mask = base["task_id"].astype(str) == str(task_id)
    for k, v in updates.items():
        base.loc[mask, k] = v
    write_csv("data/tasks.csv", base, f"Update task {task_id}")

def mark_done(task_id):
    update_task(task_id, {"status": "Done"})

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

# get selected event
event_id = st.session_state.get("selected_event_id")
if not event_id:
    st.warning("No event selected.")
    st.stop()

event = events[events["event_id"] == event_id]
if event.empty:
    st.error("Event not found.")
    st.stop()

e = event.iloc[0]

# normalize tasks
tasks["due"] = tasks["due_date"].apply(parse_date)
event_tasks = tasks[tasks["event_id"] == event_id].copy()

# --------------------------------------------------
# EVENT HEADER
# --------------------------------------------------
st.title(f"🏐 {e['event_name']}")

st.write(f"📍 **Location:** {e['location']}")
st.write(f"🗓️ **Dates:** {e['start_date']} → {e['end_date']}")
st.write(f"📌 **Status:** {e['status']}")

st.divider()

# --------------------------------------------------
# EVENT TASK LIST (SAME AS TASK PAGE)
# --------------------------------------------------
st.subheader("📝 Event tasks")

if event_tasks.empty:
    st.info("No tasks for this event.")
else:
    event_tasks["is_done"] = event_tasks["status"] == "Done"
    event_tasks = event_tasks.sort_values(["is_done","due","task_name"])

    for _, r in event_tasks.iterrows():
        task_id = str(r["task_id"])
        is_done = r["status"] == "Done"
        overdue = (r["due"] and r["due"] < today) and not is_done

        icon = "✅" if is_done else ("🔴" if overdue else "🟨")

        with st.container(border=True):
            left, right = st.columns([6,1])

            with left:
                if st.button(
                    f"{icon} {r['task_name']}",
                    key=f"open_task_{task_id}",
                ):
                    st.session_state["popup_task_id"] = task_id
                    st.session_state["show_task_popup"] = True

                st.caption(
                    f"Due: {r['due_date']} | Owner: {r['owner']} | Status: {r['status']}"
                )

            with right:
                if not is_done:
                    if st.button("✔ Done", key=f"done_task_{task_id}"):
                        mark_done(task_id)
                        st.success("Task marked as done.")
                        st.rerun()

# --------------------------------------------------
# TASK POPUP (EDIT / MARK DONE)
# --------------------------------------------------
if st.session_state.get("show_task_popup"):
    task_id = st.session_state.get("popup_task_id")
    row = tasks[tasks["task_id"].astype(str) == str(task_id)]

    if not row.empty:
        t = row.iloc[0]

        @st.dialog("📝 Task details")
        def task_dialog():
            st.markdown(f"### {t['task_name']}")

            with st.form("edit_task_form"):
                c1, c2 = st.columns(2)

                with c1:
                    task_name = st.text_input("Task name", value=t["task_name"])
                    due_date  = st.text_input("Due date (YYYY-MM-DD)", value=str(t["due_date"]))
                    owner     = st.text_input("Owner", value=str(t["owner"]))
                    status_in = st.selectbox(
                        "Status",
                        TASK_STATUS,
                        index=TASK_STATUS.index(t["status"]) if t["status"] in TASK_STATUS else 0
                    )

                with c2:
                    priority = st.text_input("Priority", value=str(t["priority"]))
                    category = st.text_input("Category", value=str(t["category"]))

                notes = st.text_area("Notes", value=str(t["notes"]))

                st.divider()
                b1, b2, b3 = st.columns(3)

                save = b1.form_submit_button("💾 Save")
                done = b2.form_submit_button("✔ Mark done")
                close = b3.form_submit_button("Close")

            if save:
                update_task(
                    t["task_id"],
                    {
                        "task_name": task_name,
                        "due_date": due_date,
                        "owner": owner,
                        "status": status_in,
                        "priority": priority,
                        "category": category,
                        "notes": notes,
                    }
                )
                st.session_state["show_task_popup"] = False
                st.success("Task updated.")
                st.rerun()

            if done:
                mark_done(t["task_id"])
                st.session_state["show_task_popup"] = False
                st.success("Task completed.")
                st.rerun()

            if close:
                st.session_state["show_task_popup"] = False
                st.rerun()

        task_dialog()
