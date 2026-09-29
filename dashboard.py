"""
Linux Server Monitoring Dashboard
Interactive web dashboard built with Streamlit, Pandas, and Plotly.
Visualizes metrics, service health, network reachability, logs, and incidents from SQLite.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure path so imports work seamlessly
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config_manager import config_manager
from database import db_manager
from system_monitor import system_monitor

# Page Configuration
st.set_page_config(
    page_title="Linux Server Monitoring Dashboard",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
        /* General page layout */
        .main {
            background-color: #0e1117;
        }
        /* Header badge */
        .metric-card {
            background: linear-gradient(135deg, #1e222d 0%, #252b3b 100%);
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 16px 20px;
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #8b949e;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #f0f6fc;
        }
        .status-badge-healthy {
            display: inline-block;
            background-color: #238636;
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .status-badge-warning {
            display: inline-block;
            background-color: #d29922;
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .status-badge-critical {
            display: inline-block;
            background-color: #da3633;
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
        }
        .section-header {
            font-size: 1.3rem;
            font-weight: 600;
            color: #58a6ff;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #21262d;
            padding-bottom: 0.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_status_badge_html(status: str) -> str:
    """Generates HTML badge for status values."""
    s = (status or "HEALTHY").upper()
    if "CRIT" in s or "FAIL" in s or "DOWN" in s:
        return f'<span class="status-badge-critical">CRITICAL</span>'
    elif "WARN" in s or "HIGH" in s:
        return f'<span class="status-badge-warning">WARNING</span>'
    elif "OK" in s or "HEALTHY" in s or "ACTIVE" in s or "UP" in s:
        return f'<span class="status-badge-healthy">HEALTHY</span>'
    return f'<span class="status-badge-warning">{status}</span>'


# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(
        "https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Linux-Dark.svg",
        width=60,
    )
    st.title("Server Monitor")
    st.caption("DevOps L1 Automated Observability System")
    st.divider()

    st.subheader("⚙️ Control Panel")

    # Manual Health Check trigger
    if st.button("🚀 Run Instant Health Check", use_container_width=True):
        with st.spinner("Executing monitoring cycle..."):
            from server_monitor import ServerMonitorOrchestrator
            orch = ServerMonitorOrchestrator()
            res = orch.run_cycle()
            st.success(f"Checked! Overall Status: {res['overall_status']}")
            st.rerun()

    # Time range selector for historical graphs
    time_filter = st.selectbox(
        "⏳ Historical Time Window",
        options=["Last 1 hour", "Last 6 hours", "Last 24 hours", "All Time"],
        index=2,
    )

    hours_map = {
        "Last 1 hour": 1,
        "Last 6 hours": 6,
        "Last 24 hours": 24,
        "All Time": None,
    }
    selected_hours = hours_map[time_filter]

    st.divider()
    st.subheader("📋 System Metadata")
    st.text(f"DB Path: {db_manager.db_path.name}")
    st.text(f"Interval: {config_manager.config['monitoring']['interval_seconds']}s")
    st.text(f"Auto-Restart: {'Enabled' if config_manager.is_auto_restart_enabled else 'Disabled'}")

    st.caption("Press 'R' or refresh browser to reload.")


# ==================== MAIN CONTENT ====================
st.title("🖥️ Linux Server Monitoring Dashboard")
st.markdown("Automated metrics collection, incident detection, and self-healing service monitoring.")

# Fetch latest system metric
latest_metric = db_manager.get_latest_system_metric()

# SECTION 1: SERVER OVERVIEW
st.markdown('<div class="section-header">Section 1: Server Overview</div>', unsafe_allow_html=True)

if latest_metric:
    col1, col2, col3, col4, col5 = st.columns(5)

    cpu_val = latest_metric["cpu"]
    mem_val = latest_metric["memory"]
    disk_val = latest_metric["disk"]
    load_val = latest_metric["load_average"]
    status_val = latest_metric["status"]

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">CPU Utilization</div>
                <div class="metric-value">{cpu_val}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Memory Utilization</div>
                <div class="metric-value">{mem_val}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Disk Usage</div>
                <div class="metric-value">{disk_val}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Load (1m)</div>
                <div class="metric-value">{load_val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col5:
        badge = get_status_badge_html(status_val)
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">System Status</div>
                <div style="margin-top: 8px;">{badge}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(f"Last recorded snapshot: **{latest_metric['timestamp']}** | Total processes: **{latest_metric['process_count']}**")
else:
    st.info("No system metrics recorded yet. Click 'Run Instant Health Check' in the sidebar or run server_monitor.py.")


# SECTION 2: RESOURCE USAGE HISTORICAL CHARTS
st.markdown('<div class="section-header">Section 2: Resource Usage Trends</div>', unsafe_allow_html=True)

metrics_history = db_manager.get_recent_system_metrics(hours=selected_hours)
if metrics_history:
    df_metrics = pd.DataFrame(metrics_history)
    df_metrics["timestamp"] = pd.to_datetime(df_metrics["timestamp"])

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # CPU & Memory Time Series
        fig_cpu_mem = go.Figure()
        fig_cpu_mem.add_trace(
            go.Scatter(
                x=df_metrics["timestamp"],
                y=df_metrics["cpu"],
                mode="lines+markers",
                name="CPU %",
                line=dict(color="#58a6ff", width=2),
                fill="tozeroy",
                fillcolor="rgba(88, 166, 255, 0.1)",
            )
        )
        fig_cpu_mem.add_trace(
            go.Scatter(
                x=df_metrics["timestamp"],
                y=df_metrics["memory"],
                mode="lines+markers",
                name="Memory %",
                line=dict(color="#bc8cff", width=2),
                fill="tozeroy",
                fillcolor="rgba(188, 140, 255, 0.1)",
            )
        )
        # Threshold reference line
        fig_cpu_mem.add_hline(
            y=config_manager.system_thresholds.get("cpu_threshold_percent", 80),
            line_dash="dot",
            line_color="#da3633",
            annotation_text="CPU/Mem Threshold (80%)",
        )
        fig_cpu_mem.update_layout(
            title="CPU & Memory Utilization (%)",
            xaxis_title="Time",
            yaxis_title="Percentage (%)",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            height=300,
            yaxis=dict(range=[0, 105]),
        )
        st.plotly_chart(fig_cpu_mem, use_container_width=True)

    with chart_col2:
        # Disk Usage Time Series
        fig_disk = go.Figure()
        fig_disk.add_trace(
            go.Scatter(
                x=df_metrics["timestamp"],
                y=df_metrics["disk"],
                mode="lines+markers",
                name="Disk %",
                line=dict(color="#3fb950", width=2),
                fill="tozeroy",
                fillcolor="rgba(63, 185, 80, 0.1)",
            )
        )
        fig_disk.add_hline(
            y=config_manager.system_thresholds.get("disk_threshold_percent", 80),
            line_dash="dot",
            line_color="#da3633",
            annotation_text="Disk Threshold (80%)",
        )
        fig_disk.update_layout(
            title="Disk Space Usage (%)",
            xaxis_title="Time",
            yaxis_title="Disk Used (%)",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=40, b=20),
            height=300,
            yaxis=dict(range=[0, 105]),
        )
        st.plotly_chart(fig_disk, use_container_width=True)
else:
    st.info("Insufficient historical metric data to plot charts.")


# SECTION 3 & 4 & 5: SERVICES, NETWORK & PORTS
row2_col1, row2_col2 = st.columns([1, 1])

with row2_col1:
    st.markdown('<div class="section-header">Section 3: Important Linux Services</div>', unsafe_allow_html=True)
    services_data = db_manager.get_latest_service_statuses()
    if services_data:
        df_services = pd.DataFrame(services_data)[["service", "status", "timestamp"]]
        df_services.columns = ["Service Name", "Status", "Last Checked"]
        st.dataframe(df_services, use_container_width=True, hide_index=True)
    else:
        st.info("No service checks recorded.")

    st.markdown('<div class="section-header">Section 5: TCP Port Availability</div>', unsafe_allow_html=True)
    ports_data = db_manager.get_latest_port_checks()
    if ports_data:
        df_ports = pd.DataFrame(ports_data)[["host", "port", "is_open", "status", "timestamp"]]
        df_ports["is_open"] = df_ports["is_open"].apply(lambda x: "OPEN" if x == 1 else "CLOSED")
        df_ports.columns = ["Host", "Port", "State", "Status", "Last Checked"]
        st.dataframe(df_ports, use_container_width=True, hide_index=True)
    else:
        st.info("No port checks recorded.")

with row2_col2:
    st.markdown('<div class="section-header">Section 4: Network Connectivity & Latency</div>', unsafe_allow_html=True)
    net_data = db_manager.get_latest_network_metrics()
    if net_data:
        df_net = pd.DataFrame(net_data)[["host", "reachable", "latency", "status", "timestamp"]]
        df_net["reachable"] = df_net["reachable"].apply(lambda x: "REACHABLE" if x == 1 else "UNREACHABLE")
        df_net["latency"] = df_net["latency"].apply(lambda x: f"{x} ms" if pd.notnull(x) else "N/A")
        df_net.columns = ["Host", "Connectivity", "Latency", "Status", "Last Checked"]
        st.dataframe(df_net, use_container_width=True, hide_index=True)
    else:
        st.info("No network checks recorded.")

    st.markdown('<div class="section-header">Section 6: Top Running Processes</div>', unsafe_allow_html=True)
    top_procs = system_monitor.get_top_processes(limit=5)
    tab_cpu, tab_mem = st.tabs(["Top CPU Processes", "Top Memory Processes"])
    with tab_cpu:
        st.dataframe(pd.DataFrame(top_procs["top_cpu"]), use_container_width=True, hide_index=True)
    with tab_mem:
        st.dataframe(pd.DataFrame(top_procs["top_memory"]), use_container_width=True, hide_index=True)


# SECTION 7: INCIDENT HISTORY
st.markdown('<div class="section-header">Section 7: Incident History & Auto-Recovery</div>', unsafe_allow_html=True)

sev_filter_col1, _ = st.columns([1, 3])
with sev_filter_col1:
    selected_sev = st.selectbox("Filter by Severity", ["ALL", "CRITICAL", "WARNING", "INFO"])

incidents = db_manager.get_incidents(severity=selected_sev, limit=50)
if incidents:
    df_incidents = pd.DataFrame(incidents)[
        ["timestamp", "severity", "incident_type", "resource", "message", "recovery_status"]
    ]
    df_incidents.columns = ["Timestamp", "Severity", "Incident Type", "Resource", "Message", "Recovery Status"]
    st.dataframe(df_incidents, use_container_width=True, hide_index=True)
else:
    st.success("No incidents recorded for the selected filter.")


# SECTION 8: RECENT LOG EVENTS
st.markdown('<div class="section-header">Section 8: Monitored Log Events</div>', unsafe_allow_html=True)

log_events = db_manager.get_recent_log_events(limit=25)
if log_events:
    df_logs = pd.DataFrame(log_events)[["timestamp", "source", "severity", "message"]]
    df_logs.columns = ["Timestamp", "Log Source", "Severity", "Message"]
    st.dataframe(df_logs, use_container_width=True, hide_index=True)
else:
    st.info("No anomalous log events detected in monitored log files.")
