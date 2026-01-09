import calendar
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from lib.data_store import read_csv, write_csv

# --------------------------------------------------
# PAGE
# --------------------------------------------------
st.set_page_config(page_title="Event Ops", layout="wide")
st.title("🏐 Event Operations Dashboard")

EVENT_COLS = ["event_id","event_name","location","start_date","end_date","status"]
TASK_COLS  = ["task_id","scope","event_id","task_name","due_date","owner","status","priority","category","notes"]

TASK_STATUS = ["Not started","In progress","Done","Blocked"]
SCOPE = ["General","Event"]

today = date.today()

# --------------------------------------------------
# CSS (KEEP YOUR BADGES)
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

def next_int_id(df, col):
    if df.empty:
        return 1
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return int(s.max()) + 1 if not s.empty else 1

def update_task(task_id, updates):
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

tasks["scope"] = tasks["scope"].astype(str).fillna("")
tasks.loc[tasks["scope"].str.strip() == "", "scope"] = "General"

events["start"] = events["start_date"].apply(parse_date)
events["end"]   = events["end_date"].apply(parse_date)
tasks["due"]    = tasks["due_date"].apply(parse_date)

tasks = tasks.merge(events[["event_id","event_name"]], on="event_id", how="left")
tasks["event_name"] = tasks["event_name"].fillna("")

def tasks_for_day(d):
    return tasks[tasks["due"] == d]

# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------
st.subheader("Dashboard")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Events", len(events))
c2.metric("Ongoing", len(events[(events["start"]<=today)&(events["end"]>=today)]))
c3.metric("Upcoming 14d", len(events[(events["start"]>today)&(events["start"]<=today+timedelta(days=14))]))
c4.metric("Overdue tasks", len(tasks[(tasks["due"]<today)&(tasks["status"]!="Done")]))

st.divider()

# --------------------------------------------------
# CALENDAR
# --------------------------------------------------
st.subheader("Calendar")

m1,m2 = st.columns(2)
with m1:
    year = st.number_input("Year", 2000, 2100, today.year)
with m2:
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)

# Day names
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

            td = tasks_for_day(d)
            label = f"{d.day} ⭐" if d == today else str(d.day)

            st.markdown(f"<div class='day {'empty' if td.empty else ''}'>", unsafe_allow_html=True)

            if st.button(label, key=f"day_{d}"):
                st.session_state["popup_date"] = d.isoformat()
                st.session_state["show_day_popup"] = True

            # ✅ RESTORED BADGE STYLE (NO TEXT)
            if not td.empty:
                st.markdown(
                    f"<span class='badge b-tk'>🟨 T {len(td)}</span>",
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------
# DAY POPUP
# --------------------------------------------------
if st.session_state.get("show_day_popup"):
    d = parse_date(st.session_state.get("popup_date"))

    @st.dialog(f"📅 {d}")
    def day_dialog():
        day_tasks = tasks_for_day(d)

        st.markdown("### 📝 Tasks")

        if day_tasks.empty:
            st.info("No tasks for this date.")
        else:
            for _, r in day_tasks.iterrows():
                is_done = r["status"] == "Done"
                overdue = (d < today) and not is_done
                icon = "✅" if is_done else ("🔴" if overdue else "🟨")

                left, right = st.columns([6,1])
                with left:
                    st.write(f"{icon} **{r['task_name']}** — {r['event_name'] or 'General'}")
                with right:
                    if not is_done:
                        if st.button("✔", key=f"done_{r['task_id']}"):
                            mark_done(r["task_id"])
                            st.rerun()

        st.divider()

        st.markdown("### ➕ Add task")

        with st.form("add_task_popup"):
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
            notes = st.text_area("Notes")

            add = st.form_submit_button("Add task")

        if add:
            base = read_csv("data/tasks.csv", TASK_COLS)
            new_id = str(next_int_id(base,"task_id"))
            row = {
                "task_id": new_id,
                "scope": scope_in,
                "event_id": event_id if scope_in=="Event" else "",
                "task_name": task_name,
                "due_date": d.isoformat(),
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

        if st.button("Close"):
            st.session_state["show_day_popup"] = False
            st.rerun()

    day_dialog()

# --------------------------------------------------
# 4) LEGEND
# --------------------------------------------------
st.subheader("Legend")
st.markdown("🟦 Event • 🟨 Task • 🔴 Overdue • 🟩 Ongoing")
