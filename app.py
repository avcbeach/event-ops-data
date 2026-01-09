import calendar
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv, write_csv

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

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
SCOPE = ["General","Event"]

# --------------------------------------------------
# CSS (CLEAN + COMPACT)
# --------------------------------------------------
st.markdown("""
<style>
.day {
  padding: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
}
.day.empty {
  background: #fafafa;
  border-style: dashed;
  opacity: 0.85;
}
.day.off {
  background: #ffffff;
  border: none;
  opacity: 0.35;
}
.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 12px;
}
.b-ev { background:#e8f1ff; color:#1e40af; }
.b-tk { background:#fef3c7; color:#92400e; }
.b-od { background:#fee2e2; color:#991b1b; }
.small { color:#6b7280; font-size:12px; }
</style>
""", unsafe_allow_html=True)

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

def next_int_id(df, col):
    if df.empty:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)
today = date.today()

tasks["scope"] = tasks["scope"].astype(str).fillna("")
tasks.loc[tasks["scope"] == "", "scope"] = "General"

events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

tasks = tasks.merge(events[["event_id","event_name"]], on="event_id", how="left")
tasks["event_name"] = tasks["event_name"].fillna("")

def events_for_day(d):
    return events[events.apply(lambda r: overlaps(d, r["start"], r["end"]), axis=1)]

def tasks_for_day(d):
    return tasks[tasks["due"] == d]

# --------------------------------------------------
# 1) DASHBOARD
# --------------------------------------------------
st.subheader("Dashboard")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Events", len(events))
c2.metric("Ongoing", len(events[(events["start"]<=today)&(events["end"]>=today)]))
c3.metric("Upcoming 14d", len(events[(events["start"]>today)&(events["start"]<=today+timedelta(days=14))]))
c4.metric("Overdue tasks", len(tasks[(tasks["due"]<today)&(tasks["status"]!="Done")]))

st.divider()

# --------------------------------------------------
# 2) DAY AGENDA
# --------------------------------------------------
st.subheader("Day agenda")

agenda_day = st.session_state.get("agenda_date")
agenda_day = parse_date(agenda_day) if isinstance(agenda_day,str) else agenda_day
agenda_day = agenda_day or today
st.session_state["agenda_date"] = agenda_day.isoformat()

st.write(f"**Selected date:** {agenda_day}")

st.markdown("### 🏐 Events")
ev = events_for_day(agenda_day)
if ev.empty:
    st.info("No events.")
else:
    for _, r in ev.iterrows():
        icon = "🟩" if r["status"].lower()=="ongoing" else "🟦"
        if st.button(f"{icon} {r['event_name']} ({r['location']})", key=f"ev_{r['event_id']}"):
            open_event(r["event_id"])

st.markdown("### 📝 Tasks")
td = tasks_for_day(agenda_day)
if td.empty:
    st.info("No tasks.")
else:
    for _, r in td.iterrows():
        icon = "🔴" if r["due"]<today and r["status"]!="Done" else "🟨"
        label = r["event_name"] if r["scope"]=="Event" else "General"
        if st.button(f"{icon} {r['task_name']} — {label}", key=f"tk_{r['task_id']}"):
            open_task(r["task_id"])

with st.expander("➕ Add task for this date"):
    with st.form("add_task"):
        scope_in = st.selectbox("Scope", SCOPE)
        event_id = ""
        if scope_in == "Event" and not events.empty:
            pick = st.selectbox(
                "Event",
                [f"{r['event_name']} ({r['event_id']})" for _, r in events.iterrows()]
            )
            event_id = pick.split("(")[-1].replace(")", "").strip()

        task_name = st.text_input("Task name")
        owner = st.text_input("Owner")
        status_in = st.selectbox("Status", TASK_STATUS)
        notes = st.text_area("Notes (optional)")
        add = st.form_submit_button("Add task")

    if add:
        base = read_csv("data/tasks.csv", TASK_COLS)
        new_id = str(next_int_id(base,"task_id"))
        row = {
            "task_id": new_id,
            "scope": scope_in,
            "event_id": event_id if scope_in=="Event" else "",
            "task_name": task_name,
            "due_date": agenda_day.isoformat(),
            "owner": owner,
            "status": status_in,
            "priority": "",
            "category": "",
            "notes": notes,
        }
        base = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
        write_csv("data/tasks.csv", base, f"Add task {new_id}")
        st.success("Task added.")
        st.rerun()

st.divider()

# --------------------------------------------------
# 3) CALENDAR (WITH DAY NAMES)
# --------------------------------------------------
st.subheader("Calendar")

m1,m2 = st.columns(2)
with m1:
    year = st.number_input("Year", 2000, 2100, today.year)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)

# --- DAY NAME HEADER ---
dow = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
hdr = st.columns(7)
for i, name in enumerate(dow):
    hdr[i].markdown(f"**{name}**")

cal = calendar.Calendar(firstweekday=0)
weeks = cal.monthdatescalendar(year, month)

for week in weeks:
    cols = st.columns(7)
    for i, d in enumerate(week):
        with cols[i]:
            if d.month != month:
                st.markdown(f"<div class='day off'>{d.day}</div>", unsafe_allow_html=True)
                continue

            ev_d = events_for_day(d)
            td_d = tasks_for_day(d)
            empty = len(ev_d)==0 and len(td_d)==0

            st.markdown(f"<div class='day {'empty' if empty else ''}'>", unsafe_allow_html=True)
            label = f"{d.day} ⭐" if d == today else str(d.day)
            if st.button(label, key=f"d_{d}"):
                st.session_state["agenda_date"] = d.isoformat()
                st.rerun()

            if not empty:
                if len(ev_d)>0:
                    st.markdown(f"<span class='badge b-ev'>E {len(ev_d)}</span>", unsafe_allow_html=True)
                if len(td_d)>0:
                    st.markdown(f"<span class='badge b-tk'>T {len(td_d)}</span>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# --------------------------------------------------
# 4) LEGEND
# --------------------------------------------------
st.subheader("Legend")
st.markdown("🟦 Event • 🟨 Task • 🔴 Overdue • 🟩 Ongoing")
