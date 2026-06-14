import streamlit as st
import requests
import json

st.set_page_config(page_title="AI Travel Agent", page_icon="✈️")
st.title("✈️ AI Travel Agent")

# ---- 侧边栏：登录/注册 ----
with st.sidebar:
    st.header("🔐 登录")

    API_URL = "http://127.0.0.1:8000"

    # 用 session_state 记住登录状态
    if "token" not in st.session_state:
        st.session_state.token = None

    if st.session_state.token:
        st.success("已登录 ✅")
        if st.button("退出登录"):
            st.session_state.token = None
            st.session_state.messages = []
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("登录"):
                r = requests.post(f"{API_URL}/login", json={
                    "username": username,
                    "password": password
                })
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.token = data.get("token")
                    st.rerun()
                else:
                    st.error("登录失败")

        with tab2:
            new_user = st.text_input("用户名", key="reg_username")
            new_pass = st.text_input("密码", type="password", key="reg_password")
            if st.button("注册"):
                r = requests.post(f"{API_URL}/register", json={
                    "username": new_user,
                    "password": new_pass
                })
                if r.status_code == 200:
                    st.success("注册成功，去登录吧")
                else:
                    st.error("注册失败")

# ---- 主区域：聊天 ----
if st.session_state.token is None:
    st.info("👈 先在侧边栏登录或注册")
else:
    # 初始化消息历史
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 聊天输入框
    if prompt := st.chat_input("说说你的旅行想法..."):

        # 显示用户消息
        with st.chat_message("user"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 调后端流式接口
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                resp = requests.post(
                    f"{API_URL}/agent/stream",
                    json={"message": prompt},
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    stream=True,
                    timeout=60
                )

                content_type = resp.headers.get("content-type", "")

                if "text/event-stream" in content_type:
                    for line in resp.iter_lines():
                        if line:
                            line_str = line.decode("utf-8")
                            if line_str.startswith("data: ") and "[DONE]" not in line_str:
                                try:
                                    chunk = json.loads(line_str[6:])
                                    full_response += chunk.get("content", "")
                                    placeholder.markdown(full_response + "▌")
                                except:
                                    pass
                    placeholder.markdown(full_response)

                else:
                    try:
                        data = json.loads(resp.text)
                        full_response = data.get("answer", data.get("message", str(data)))
                    except:
                        full_response = resp.text
                    placeholder.markdown(full_response)

            except Exception as e:
                placeholder.error(f"连接失败: {e}")

        st.session_state.messages.append({"role": "assistant", "content": full_response})
