"""Streamlit frontend for the AWS Agentic Agent."""

import os
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Agentic AWS Chatbot", layout="centered")
st.title("Agentic AWS Chatbot")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Say something...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state["messages"].append({"role": "user", "content": user_input})

    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{API_URL}/chat",
                    json={
                        "message": user_input,
                        "history": st.session_state["messages"],
                    },
                )
                response.raise_for_status()

            data: dict[str, Any] = response.json()
            reply = data.get("response", "No reply received.")
            st.session_state["messages"] = data.get("updated_history", st.session_state["messages"])
            st.markdown(reply)

        except httpx.HTTPStatusError as e:
            error_msg = f"Error: Server returned {e.response.status_code}"
            st.markdown(error_msg)
            st.session_state["messages"].append({"role": "assistant", "content": error_msg})

        except httpx.RequestError as e:
            error_msg = f"Error communicating with backend: {e}"
            st.markdown(error_msg)
            st.session_state["messages"].append({"role": "assistant", "content": error_msg})
