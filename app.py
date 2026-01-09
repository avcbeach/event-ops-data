import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv

# --------------------------------------------------
# CLEAR NAV STATE
# --------------------------------------------------
st.session_state.pop("selected_task_id", None)
st.session_state.pop("selected_event_id", None)

# --------------------------------------------------
# PAGE
# --------------------------------------------------
st.set_page_config(page_title="Event Ops", layout="wide")
st.title("🏐 Event Operations Dashboard")

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except:
        return None

def overlaps(d, s, e):
    return bool(s and e and s <= d <= e)

def open_event(eid):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

def open_task(tid):
    st.session_state["selected_task_id"] = tid
    st.switch_page("pages/3_Tasks.py")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

today = date.today()

events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

tasks["scope"] = tasks["scope"].astype(str).fillna("")
tasks.loc[tasks["scope"].eq(""), "scope"] = "General"

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------
ongoing = events[(events["start"] <= today) & (events["end"] >= today)]
upcoming = events[(events["start"] > today)]
overdue = tasks[(tasks["due"] < today) & (tasks["status"]!="Done")]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total events", len(events))
c2.metric("Ongoing", len(ongoing))
c3.metric("Upcoming", len(upcoming))
c4.metric("Overdue tasks", len(overdue))

st.divider()

# --------------------------------------------------
# LEGEND (EXPLAIN COLORS CLEARLY)
# --------------------------------------------------
st.subheader("Legend")

l1,l2,l3,l4 = st.columns(4)
l1.markdown("🟦 **Event (planned / upcoming)**")
l2.markdown("🟩 **Event (ongoing)**")
l3.markdown("🟨 **Task due**")
l4.markdown("🔴 **Overdue task**")

st.divider()

# --------------------------------------------------
# DATE SELECTOR
# --------------------------------------------------
st.subheader("📅 Select date")
selected_date = st.date_input(
    "Choose a date to view agenda",
    value=st.session_state.get("agenda_date", today),
)

st.session_state["agenda_date"] = selected_date

# --------------------------------------------------
# AGENDA (MAIN CONTENT)
# --------------------------------------------------
st.subheader(f"📌 Agenda — {selected_date}")

# EVENTS
st.markdown("### 🏐 Events")
ev = events[events.apply(lambda r: overlaps(selected_date, r["start"], r["end"]), axis=1)]

if ev.empty:
    st.info("No events on this day.")
else:
    for _, r in ev.iterrows():
        icon = "🟩" if r["status"].lower()=="ongoing" else "🟦"
        if st.button(f"{icon} {r['event_name']} ({r['location']})", key=f"ev_{r['event_id']}"):
            open_event(r["event_id"])

# TASKS
st.markdown("### 📝 Tasks")
td = tasks[tasks["due"] == selected_date]

if td.empty:
    st.info("No tasks due on this day.")
else:
    for _, r in td.iterrows():
        icon = "🔴" if (r["status"]!="Done" and r["due"] < today) else "🟨"
        if st.button(f"{icon} {r['task_name']}", key=f"tk_{r['task_id']}"):
            open_task(r["task_id"])

# --------------------------------------------------
# UPCOMING / OVERDUE QUICK VIEW
# --------------------------------------------------
st.divider()
st.subheader("⚠️ Attention")

c1,c2 = st.columns(2)

with c1:
    st.markdown("### 🔴 Overdue tasks")
    if overdue.empty:
        st.info("No overdue tasks.")
    else:
        for _, r in overdue.iterrows():
            if st.button(f"🔴 {r['task_name']} (due {r['due_date']})", key=f"od_{r['task_id']}"):
                open_task(r["task_id"])

with c2:
    st.markdown("### ⏭️ Next 7 days")
    soon = tasks[(tasks["due"] >= today) & (tasks["due"] <= today + timedelta(days=7))]
    if soon.empty:
        st.info("No tasks in next 7 days.")
    else:
        for _, r in soon.iterrows():
            if st.button(f"🟨 {r['task_name']} ({r['due_date']})", key=f"nx_{r['task_id']}"):
                open_task(r["task_id"])
