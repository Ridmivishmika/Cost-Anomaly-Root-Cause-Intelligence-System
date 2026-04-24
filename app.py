import pandas as pd
import streamlit as st

from carci.analysis import build_analysis_result


st.set_page_config(
    page_title="CARCI — Cost Anomaly Root Cause Intelligence",
    page_icon="📈",
    layout="wide",
)


PAGE_CSS = """
<style>
body {
    background: linear-gradient(135deg, #f8fafc 0%, #ecfeff 100%);
}
header[data-testid="top-bar"] {
    background: transparent !important;
}
.css-1d391kg,
.stApp {
    background: transparent !important;
}
.carci-header {
    border-radius: 24px;
    background: linear-gradient(90deg, #047857 0%, #0f766e 100%);
    color: white;
    padding: 2rem 2.5rem;
    box-shadow: 0 30px 60px rgba(15, 23, 42, 0.08);
    margin-bottom: 2rem;
}
.carci-header h1 {
    margin: 0;
    font-size: 3rem;
    letter-spacing: -0.04em;
}
.carci-header p {
    margin: 0.75rem 0 0;
    color: #d1fae5;
    font-size: 1.05rem;
}
.carci-card {
    border-radius: 24px;
    background: white;
    padding: 2rem;
    box-shadow: 0 20px 50px rgba(15, 23, 42, 0.05);
    border: 1px solid #e2e8f0;
    margin-bottom: 1.5rem;
}
.carci-upload-box {
    border: 2px dashed #cbd5e1;
    border-radius: 24px;
    padding: 2rem;
    text-align: center;
    transition: border-color 0.25s ease, background-color 0.25s ease;
    background: #f8fafc;
    margin-bottom: 1.5rem;
}
.carci-upload-box:hover {
    border-color: #10b981;
    background: #ecfdf5;
}
.upload-label {
    margin: 0;
    color: #334155;
    font-size: 0.95rem;
}
.upload-name {
    margin: 0.5rem 0 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
}
.carci-small-note {
    color: #475569;
    margin-top: 0.75rem;
}
.carci-table th {
    background: #f8fafc !important;
}
</style>
"""


def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file, skipinitialspace=True)


def main() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="carci-header">
            <div style="display:flex; align-items:center; gap:1rem; flex-wrap:wrap;">
                <div style="width:3rem; height:3rem; border-radius:14px; background:rgba(255,255,255,0.18); display:flex; align-items:center; justify-content:center; font-size:1.5rem;">📈</div>
                <div>
                    <h1>CARCI</h1>
                    <p>Service anomaly detection and root-cause analysis for AWS billing data.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "analysis_error" not in st.session_state:
        st.session_state.analysis_error = None

    uploaded_file = st.file_uploader("Upload your AWS CUR CSV", type=["csv"], help="Upload a CUR-style CSV file.")

    if uploaded_file:
        st.markdown(
            f"""
            <div class='carci-upload-box'>
                <p class='upload-label'>Selected file:</p>
                <p class='upload-name'>{uploaded_file.name}</p>
                <p class='carci-small-note'>CSV upload is ready. Click Start Analysis to continue.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class='carci-upload-box'>
                <p class='upload-label'>No file selected yet.</p>
                <p class='upload-name'>Please upload a CUR CSV to begin.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if uploaded_file and st.button("Start Analysis"):
        st.session_state.analysis_error = None
        with st.spinner("Analyzing your AWS CUR data..."):
            try:
                raw_df = load_uploaded_csv(uploaded_file)
                st.session_state.analysis_result = build_analysis_result(raw_df)
            except Exception as exc:
                st.session_state.analysis_error = str(exc)
                st.session_state.analysis_result = None

    if st.session_state.analysis_error:
        st.error(f"Unable to analyze the uploaded file: {st.session_state.analysis_error}")

    if st.session_state.analysis_result:
        st.success("Analysis complete. Review the anomaly summary below.")

        service_table = pd.DataFrame(st.session_state.analysis_result["service_comparison"]).rename(
            columns={
                "service_name": "Service",
                "anomaly_value": "Anomaly Cost",
                "normal_value": "Normal Cost",
                "percentage": "Percentage",
                "impact_value": "Impact",
            }
        )[["Service", "Anomaly Cost", "Normal Cost", "Impact", "Percentage"]]

        st.markdown("<div class='carci-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='margin-bottom:0.5rem; color:#0f172a;'>Service Anomaly Table</h2>", unsafe_allow_html=True)
        st.markdown("<p class='carci-small-note'>Detected anomalies sorted by impact and percentage change.</p>", unsafe_allow_html=True)
        st.dataframe(service_table, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<h2 style='margin-bottom:0.5rem; color:#0f172a;'>Root Cause Analysis</h2>", unsafe_allow_html=True)
        for service_root_cause in st.session_state.analysis_result["service_root_causes"]:
            with st.expander(service_root_cause["service_name"], expanded=False):
                st.write(service_root_cause["root_cause_analysis"])

        if st.button("Upload New File"):
            st.session_state.analysis_result = None
            st.session_state.analysis_error = None
            st.experimental_rerun()


if __name__ == "__main__":
    main()
