import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Lameteo.cat · Visor meteorològic",
    page_icon="🌦️",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
    max-width: 100%;
}
</style>
""", unsafe_allow_html=True)

html = """
<iframe 
src="https://www.rainviewer.com/map.html?loc=41.4033,2.1734,7&oFa=0&oC=1&oU=0&oCS=1&oF=0&oAP=1&c=1&o=83&lm=1&layer=radar&sm=1&sn=1"
style="width:100%;height:820px;border:0;border-radius:22px;overflow:hidden;">
</iframe>
"""

st.title("🌦️ Lameteo.cat · Radar i satèl·lit")
st.caption("Visor meteorològic experimental amb radar de pluja en temps real.")

components.html(html, height=850)
