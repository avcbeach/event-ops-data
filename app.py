import streamlit as st
from lib.data_store import read_csv

st.title("Event Ops App – Test")

token = st.secrets["GITHUB_TOKEN"]

df, sha = read_csv("data/events.csv", token)

st.success("Connected to GitHub")
st.write("Rows loaded:", len(df))
st.dataframe(df)

