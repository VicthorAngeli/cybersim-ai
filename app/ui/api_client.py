import httpx
import streamlit as st

from app.core.config import get_settings


def api_request(method: str, path: str, **kwargs) -> tuple[bool, object]:
    headers = kwargs.pop("headers", {})
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request(
            method,
            f"{get_settings().streamlit_api_url.rstrip('/')}{path}",
            headers=headers,
            timeout=30,
            **kwargs,
        )
        if response.is_error:
            try:
                details = response.json().get("detail", response.text)
            except ValueError:
                details = response.text
            return False, f"{response.status_code}: {details}"
        if response.status_code == 204:
            return True, None
        if "application/json" in response.headers.get("content-type", ""):
            return True, response.json()
        return True, response.content
    except httpx.HTTPError as exc:
        return False, f"Não foi possível conectar à API: {exc}"
