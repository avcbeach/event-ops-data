import calendar
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv

# --------------------------------------------------
# CLEAR NAV STATE (PREVENT AUTO REDIRECT)
# --------------------------------------------------
st.session_state.pop("selected_task_id", None)
st.session_state.pop("selected_event_id", None)

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------
st.set_page_config(page_title="Event Ops", layout="wide")
st.title("🏐 Event Operations Dashboard")

# --------------------------------------------------
# SCHEMAS
# --------------------------------------------------
EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

# --------------------------------------------------
# CSS (CALENDAR + PILL BUTTONS)
# --------------------------------------------------
st.markdown("""
<style>
.day-cell {
    height: 180px;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
    overflow: hidden;
    background: #ffffff;
}
.day-header {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
}

.pill-btn button {
    width: 100%;
    padding: 2px 6px;
    margin-bottom: 4px;
    border-radius: 6px;
    font-size: 12px;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Event colors */
.ev-blue button { background:#e8f1ff; color:#1e40af; }
.ev-green button { background:#e9f7ef; color:#065f46; }
.ev-grey button { background:#f3f4f6; color:#374151; }
.ev-red button { background:#fee2e2; color:#991b1b; }

/* Task colors */
.tk-yellow button { background:#fef3c7; color:#92400e; }
.tk-purple button { background:#ede9fe; color:#5b21b6; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def parse_date(s):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return None

def overlaps(day, start, end):
    return bool(start and end and start <= day <= end)

def event_class(status):
    s = str(status).lower()
    if s == "ongoing":
        return "ev-green"
    if s == "completed":
        return "ev-grey"
    if s == "cancelled":
        return "ev-red"
    return "ev-blue"

def open_event(eid):
    st.session_state["selected_event_id"] = eid
    st.switch_page("pages/2_Event_Detail.py")

def open_task(tid):
    st.session_state["selected_task_id"] = tid
    st.switch_page("pages/3_Tasks.py")

def popover_or_expander(label):
    return st.popover(label) if hasattr(st, "popover") else st.expander(label)

# --------------------------------------------------
# LOAD DATA (GITHUB-BACKED)
# --------------------------------------------------
events = read_csv("data/events.csv", EVENT_COLS)
tasks  = read_csv("data/tasks.csv", TASK_COLS)

today = date.today()

# normalize scope
tasks["scope"] = tasks["scope"].astype(str).fillna("")
blank = tasks["scope"].str.strip().eq("")
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().ne(""), "scope"] = "Event"
tasks.loc[blank & tasks["event_id"].astype(str).str.strip().eq(""), "scope"] = "General"

# parse dates
events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

# merge event name into tasks
tasks = tasks.merge(
    events[["event_id","event_name"]],
    on="event_id",
    how="left"
)
tasks["event_name"] = tasks["event_name"].fillna("")

# --------------------------------------------------
# SUMMARY
# --------------------------------------------------
ongoing = events[(events["start"] <= today) & (events["end"] >= today)]
upcoming = events[(events["start"] > today) & (events["start"] <= today + timedelta(days=14))]
overdue = tasks[(tasks["due"] < today) & (tasks["status"].str.lower() != "done")]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total events", len(events))
c2.metric("Ongoing", len(ongoing))
c3.metric("Upcoming (14 days)", len(upcoming))
c4.metric("Overdue tasks", len(overdue))

st.divider()

# --------------------------------------------------
# CALENDAR CONTROLS
# --------------------------------------------------
st.subheader("🗓️ Monthly calendar")

m1,m2,m3 = st.columns([2,2,6])
with m1:
    year = st.number_input("Year", 2000, 2100, value=today.year)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)
with m3:
    st.caption("Color-coded • fixed height • click items • +more when crowded")

cal = calendar.Calendar()
weeks = cal.monthdatescalendar(int(year), int(month))

def events_for_day(d):
    return events[events.apply(lambda r: overlaps(d, r["start"], r["end"]), axis=1)]

def tasks_for_day(d):
    return tasks[tasks["due"] == d]

# header
dow = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
cols = st.columns(7)
for i, name in enumerate(dow):
    cols[i].markdown(f"**{name}**")

MAX_ITEMS = 3

# --------------------------------------------------
# CALENDAR GRID (FIXED + SAFE)
# --------------------------------------------------
for week in weeks:
    cols = st.columns(7, gap="small")
    for i, d in enumerate(week):
        with cols[i]:
            st.markdown("<div class='day-cell'>", unsafe_allow_html=True)

            st.markdown(
                f"<div class='day-header'>{d.day}{' ⭐' if d == today else ''}</div>",
                unsafe_allow_html=True
            )

            if d.month == month:
                if st.button("Agenda", key=f"day_{d.isoformat()}"):
                    st.session_state["agenda_date"] = d.isoformat()

                ev = events_for_day(d)
                td = tasks_for_day(d)

                shown = 0

                for _, r in ev.iterrows():
                    if shown >= MAX_ITEMS:
                        break
                    with st.container():
                        st.markdown(f"<div class='pill-btn {event_class(r['status'])}'>", unsafe_allow_html=True)
                        if st.button(
                            r["event_name"],
                            key=f"cal_ev_{d.isoformat()}_{r['event_id']}"
                        ):
                            open_event(r["event_id"])
                        st.markdown("</div>", unsafe_allow_html=True)
                    shown += 1

                for _, r in td.iterrows():
                    if shown >= MAX_ITEMS:
                        break
                    css = "tk-purple" if r["scope"] == "Event" else "tk-yellow"
                    with st.container():
                        st.markdown(f"<div class='pill-btn {css}'>", unsafe_allow_html=True)
                        if st.button(
                            r["task_name"],
                            key=f"cal_tk_{d.isoformat()}_{r['task_id']}"
                        ):
                            open_task(r["task_id"])
                        st.markdown("</div>", unsafe_allow_html=True)
                    shown += 1

                remaining = len(ev) + len(td) - shown
                if remaining > 0:
                    with popover_or_expander(f"+{remaining} more"):
                        for _, r in ev.iterrows():
                            if st.button(r["event_name"], key=f"pev_{d}_{r['event_id']}"):
                                open_event(r["event_id"])
                        for _, r in td.iterrows():
                            if st.button(r["task_name"], key=f"ptk_{d}_{r['task_id']}"):
                                open_task(r["task_id"])

            st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# DAY AGENDA
# --------------------------------------------------
st.divider()
st.subheader("📌 Day agenda")

agenda_iso = st.session_state.get("agenda_date")
agenda_day = parse_date(agenda_iso) if agenda_iso else None

if not agenda_day:
    st.info("Click Agenda on a day to view details.")
else:
    st.write(f"**{agenda_day.isoformat()}**")

    st.markdown("### Events")
    ev = events_for_day(agenda_day)
    if ev.empty:
        st.info("No events.")
    else:
        for _, r in ev.iterrows():
            if st.button(r["event_name"], key=f"ag_ev_{r['event_id']}"):
                open_event(r["event_id"])

    st.markdown("### Tasks due")
    td = tasks_for_day(agenda_day)
    if td.empty:
        st.info("No tasks.")
    else:
        for _, r in td.iterrows():
            if st.button(r["task_name"], key=f"ag_tk_{r['task_id']}"):
                open_task(r["task_id"])
