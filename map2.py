# ultrapremium_dashboard.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster
from geopy.distance import geodesic
import plotly.express as px
import os
import time
from datetime import datetime
from streamlit_plotly_events import plotly_events
import random
from math import radians, cos, sin, asin, sqrt

# optional: shapely for polygon (convex hull)
try:
    from shapely.geometry import MultiPoint
    SHAPELY_AVAILABLE = True
except Exception:
    SHAPELY_AVAILABLE = False
# -------------------------
def haversine(p1, p2):
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371000  # meter
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(a))

    while remaining:
        next_point = min(
            remaining,
            key=lambda x: haversine(current, (x[1], x[2]))
        )
        route.append(next_point)
        current = (next_point[1], next_point[2])
        remaining.remove(next_point)
    
# CONFIG
# -------------------------
DATA_PATH = "cobalagi_daerah.csv"            # ganti jika nama file CSV berbeda
NOTES_PATH = "catatan_kunjungan.csv"  # file catatan kunjungan akan dibuat jika belum ada
AUTO_REFRESH = True                   # script akan memeriksa perubahan file CSV dan reload otomatis

st.set_page_config(page_title="DASHBOARD MAPPING AREA", layout="wide", initial_sidebar_state="expanded")

# -------------------------
# CSS : Glass + Shimmer + Animations
# -------------------------
st.markdown("""
<style>
/* ====== Fonts & base ====== */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

/* ====== Header ====== */
.header {
  display:flex; align-items:center; justify-content:space-between;
  padding:16px 10px; position:sticky; top:0; z-index:999;
  backdrop-filter: blur(6px); background: rgba(255,255,255,0.03);
}

/* ====== Glass card ====== */
.glass {
  background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
  border-radius: 14px; padding: 16px; margin-bottom: 16px;
  box-shadow: 0 6px 20px rgba(7,12,20,0.5);
  border: 1px solid rgba(255,255,255,0.03);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.glass:hover { transform: translateY(-4px); box-shadow: 0 10px 30px rgba(7,12,20,0.6); }

/* ====== Map box ====== */
.map-box { border-radius:12px; overflow:hidden; box-shadow:0 8px 30px rgba(0,0,0,0.5); }

/* ====== Small metrics ====== */
.metric {
  font-size: 28px; font-weight:700; margin-top:6px;
}

/* ====== Table rounded ====== */
.stDataFrame table {
  border-radius: 10px; overflow: hidden;
}

/* ====== Shimmer skeleton ====== */
.skeleton {
  background: linear-gradient(90deg, #0f1724 25%, #111827 37%, #0f1724 63%);
  background-size: 400% 100%;
  animation: shimmer 1.8s linear infinite;
  border-radius:10px; height:160px;
}
@keyframes shimmer { 0%{background-position:100% 50%} 100%{background-position:0 50%} }

/* ====== Filter inputs styling ====== */
.filter-row { display:flex; gap:10px; align-items:center; justify-content:space-between; }

/* ====== badges ====== */
.badge {
  padding:6px 10px; border-radius:999px; font-size:12px; font-weight:600;
  background: linear-gradient(90deg, #6EE7B7, #3B82F6);
  color:#03203C;
}

/* ====== Responsive tweaks ====== */
@media (max-width: 900px) {
  .filter-row { flex-direction: column; align-items:stretch; }
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Utility: load & watch file changes
# -------------------------
def load_data(path=DATA_PATH):
    df = pd.read_csv(path)
    # basic normalization (ensure correct column names exist)
    expected = ["nama_usaha", "Jenis Usaha", "daerah", "lat", "lon", "review"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.error(f"CSV missing columns: {missing}. Pastikan kolom ada dan penamaan persis seperti yang diminta.")
        st.stop()
    # ensure numeric types
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["review"] = pd.to_numeric(df["review"], errors="coerce").fillna(0)
    return df

def ensure_notes_file(path=NOTES_PATH):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["timestamp","nama_usaha","lat","lon","catatan"])
        df.to_csv(path, index=False)

def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except:
        return None

# Check data file existence
if not os.path.exists(DATA_PATH):
    st.error(f"Data CSV '{DATA_PATH}' tidak ditemukan. Upload atau letakkan file CSV di folder yang sama.")
    st.stop()

# Auto-refresh on file change (simple watcher)
if "data_mtime" not in st.session_state:
    st.session_state.data_mtime = file_mtime(DATA_PATH)

# If file changed, reload (experimental auto refresh)
current_mtime = file_mtime(DATA_PATH)
if AUTO_REFRESH and current_mtime and current_mtime != st.session_state.data_mtime:
    st.session_state.data_mtime = current_mtime
    # small visual indicator
    st.experimental_rerun()

# -------------------------
# Load data
# -------------------------
with st.spinner("Memuat data dan komponen dashboard..."):
    data = load_data(DATA_PATH)
    ensure_notes_file()
    notes_df = pd.read_csv(NOTES_PATH) if os.path.exists(NOTES_PATH) else pd.DataFrame(columns=["timestamp","nama_usaha","lat","lon","catatan"])
time.sleep(0.05)

# -------------------------
# Sidebar: Navigation & filters
# -------------------------
st.sidebar.title("Dashboard Pemetaan & Analisis Cluster Usaha")
page = st.sidebar.radio("Navigation", ["Dashboard Utama", "Peta Radius", "Peta Cluster","Data & Catatan", "Settings",])

st.sidebar.markdown("---")
st.sidebar.markdown("**Advanced Filter**")
jenis_options = ["SEMUA"] + sorted(data["Jenis Usaha"].dropna().unique().tolist())
sel_jenis = st.sidebar.selectbox("Jenis Usaha", jenis_options)
daerah_options = ["SEMUA"] + sorted(data["daerah"].dropna().unique().tolist())
sel_daerah = st.sidebar.selectbox("Daerah", daerah_options)
min_review, max_review = st.sidebar.slider("Range Review", int(data["review"].min()), int(max(1, data["review"].max())), (int(data["review"].min()), int(max(1, data["review"].max()))))
radius_default = st.sidebar.slider("Default Radius (m)", 100, 1000, 300)
high_review_only = st.sidebar.checkbox("Only High Review (>1000)", value=False)
st.sidebar.markdown("---")
if st.sidebar.button("Reset Filter"):
    sel_jenis = "SEMUA"
    sel_daerah = "SEMUA"
    min_review, max_review = int(data["review"].min()), int(max(1, data["review"].max()))

# Apply advanced filters
df_filtered = data.copy()
if sel_jenis != "SEMUA":
    df_filtered = df_filtered[df_filtered["Jenis Usaha"] == sel_jenis]
if sel_daerah != "SEMUA":
    df_filtered = df_filtered[df_filtered["daerah"] == sel_daerah]
df_filtered = df_filtered[(df_filtered["review"] >= min_review) & (df_filtered["review"] <= max_review)]
if high_review_only:
    df_filtered = df_filtered[df_filtered["review"] > 1000]

# -------------------------
# Header
# -------------------------
st.markdown(f"<div class='header'><h2>🏢 DASHBOARD MAPPING AREA JEMBER</h2><div style='opacity:0.7'>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div>", unsafe_allow_html=True)
st.markdown("")
# -------------------------
# Pages
# -------------------------
if page == "Dashboard Utama":
    # layout
    c1, c2 = st.columns([2.2, 1])
    with c1:
        # metrics cards
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.markdown("<div style='opacity:0.7'>Total Usaha</div>", unsafe_allow_html=True)
        col_a.markdown(f"<div class='metric'>{len(data):,}</div>", unsafe_allow_html=True)

        col_b.markdown("<div style='opacity:0.7'>Setelah Filter</div>", unsafe_allow_html=True)
        col_b.markdown(f"<div class='metric'>{len(df_filtered):,}</div>", unsafe_allow_html=True)

        # compute count within default radius around a chosen center (if any)
        center_choice = st.selectbox("Pilih Titik Pusat (untuk hitung radius)", ["-- PILIH --"] + data["nama_usaha"].tolist())
        within_count = 0
        if center_choice != "-- PILIH --":
            pusat = data[data["nama_usaha"] == center_choice].iloc[0]
            def _j(r): return geodesic((pusat["lat"], pusat["lon"]), (r["lat"], r["lon"])).meters
            data["__jarak_tmp"] = data.apply(_j, axis=1)
            within_count = int(data[data["__jarak_tmp"] <= radius_default].shape[0])
        col_c.markdown("<div style='opacity:0.7'>Dalam Radius</div>", unsafe_allow_html=True)
        col_c.markdown(f"<div class='metric'>{within_count:,}</div>", unsafe_allow_html=True)

        col_d.markdown("<div style='opacity:0.7'>High Review</div>", unsafe_allow_html=True)
        col_d.markdown(f"<div class='metric'>{int((data['review']>1000).sum()):,}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        

        # main map + charts
        left_col, right_col = st.columns([2,1])
        with left_col:
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='glass map-box'>", unsafe_allow_html=True)
            st.write("### Peta Persebaran Usaha (Preview)")
            # show small folium map with markers
            if len(df_filtered) == 0:
                st.info("Tidak ada usaha yang cocok dengan filter.")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                center_lat = df_filtered["lat"].median()
                center_lon = df_filtered["lon"].median()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB dark_matter")
                mc = MarkerCluster()
                for _, r in df_filtered.iterrows():
                    folium.Marker(
                        [r["lat"], r["lon"]],
                        popup=f"<b>{r['nama_usaha']}</b><br>{r['Jenis Usaha']}<br>{r['daerah']}<br>Review: {int(r['review'])}"
                    ).add_to(mc)
                mc.add_to(m)

                # optional heatmap overlay
                heat_on = st.checkbox("Tampilkan Heatmap pada preview", value=True)
                if heat_on:
                    heat_data = df_filtered[["lat","lon"]].dropna().values.tolist()
                    HeatMap(heat_data, radius=18, blur=10, min_opacity=0.3).add_to(m)

                st_folium(m, width=900, height=520)
                st.markdown("</div>", unsafe_allow_html=True)

        with right_col:
          
            # Top daerah table
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.write("### Top Daerah dengan Usaha Terbanyak")
            daerah_count = data["daerah"].value_counts().reset_index()
            daerah_count.columns = ["daerah", "jumlah"]
            st.table(daerah_count.head(8).reset_index(drop=True))
            st.markdown("</div>", unsafe_allow_html=True)
            
              # Pie: Persentase Jenis Usaha
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.write("### Persentase Jenis Usaha")
            jenis_count = data["Jenis Usaha"].value_counts().reset_index()
            jenis_count.columns = ["Jenis Usaha", "jumlah"]
            fig = px.pie(jenis_count, names="Jenis Usaha", values="jumlah", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


    with c2:

        # Recent activity / notes summary
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.write("### Recent Notes")
        if notes_df.shape[0] == 0:
            st.info("Belum ada catatan kunjungan.")
        else:
            recent = notes_df.sort_values("timestamp", ascending=False).head(6)
            for _, row in recent.iterrows():
                st.markdown(f"**{row['nama_usaha']}** — {row['timestamp']}")
                st.markdown(f"<div style='opacity:0.7'>{row['catatan']}</div>", unsafe_allow_html=True)
                st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)

        # Top daerah chart (clickable)
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.write("### Top Daerah dengan Usaha Terbanyak")

        # Hitung jumlah usaha per daerah
        daerah_count = df_filtered["daerah"].value_counts().reset_index()
        daerah_count.columns = ["daerah", "jumlah"]

        top8 = daerah_count.head(8)

        # Buat bar chart horizontal
        fig_bar = px.bar(
            top8,
            x="jumlah",
            y="daerah",
            orientation="h",
            title="",
            labels={"jumlah": "Jumlah Usaha", "daerah": "Daerah"},
        )

        fig_bar.update_traces(textposition="outside")

        # Styling chart premium
        fig_bar.update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )

        # ⚠️ Penting! Kalau tidak ada ini, grafik TIDAK AKAN muncul
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)



elif page == "Peta Radius":
    st.write("### Peta Radius & Tabel Interaktif")
    colL, colR = st.columns([2,1])
    with colL:
        st.markdown("<div class='glass map-box'>", unsafe_allow_html=True)
        center_choice = st.selectbox("Pilih Titik Pusat:", ["-- PILIH --"] + data["nama_usaha"].tolist(), key="center_choice_map")
        radius_val = st.slider("Radius (meter)", 50, 1500, radius_default, key="radius_val")
        if center_choice == "-- PILIH --":
            st.info("Pilih titik pusat untuk menampilkan radius.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            pusat = data[data["nama_usaha"] == center_choice].iloc[0]
            m = folium.Map(location=[pusat["lat"], pusat["lon"]], zoom_start=15, tiles="CartoDB positron")
            folium.Circle(location=[pusat["lat"], pusat["lon"]], radius=radius_val, color="#4B7BEC", fill=True, fill_opacity=0.12).add_to(m)
            markers = []
            def distf(r): return geodesic((pusat["lat"], pusat["lon"]), (r["lat"], r["lon"])).meters
            data["jarak_m"] = data.apply(distf, axis=1)
            in_radius = data[data["jarak_m"] <= radius_val].copy()
            mc = MarkerCluster()
            for _, r in in_radius.iterrows():
                folium.Marker([r["lat"], r["lon"]], popup=f"<b>{r['nama_usaha']}</b><br>{r['Jenis Usaha']}<br>{r['daerah']}<br>{int(r['jarak_m'])} m").add_to(mc)
            mc.add_to(m)

            # ====== MANUAL CLUSTER BUILDER FOR RADIUS MAP ======
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("### 🎯 Buat Cluster dari Hasil Radius", unsafe_allow_html=True)

            # ensure manual_clusters exists in session
            if "manual_clusters" not in st.session_state:
                st.session_state.manual_clusters = {}

            # show quick create form (only shows items from in_radius)
            choices_radius = in_radius["nama_usaha"].astype(str).tolist()
            with st.form("create_cluster_radius_form"):
                cname_r = st.text_input("Nama Cluster Baru (Radius)")
                ccolor_r = st.color_picker("Warna Cluster", "#22c55e")
                cmembers_r = st.multiselect("Pilih usaha yang akan masuk ke cluster", choices_radius)
                create_r = st.form_submit_button("Tambah Cluster dari Radius")

            if create_r:
                if cname_r.strip() == "":
                    st.error("Nama cluster tidak boleh kosong!")
                elif len(cmembers_r) == 0:
                    st.error("Pilih minimal 1 usaha dari hasil radius untuk dimasukkan ke cluster.")
                else:
                    st.session_state.manual_clusters[cname_r] = {"color": ccolor_r, "active": True, "members": cmembers_r}
                    st.success(f"Cluster '{cname_r}' ditambahkan dan akan muncul di peta radius.")

            # List & edit existing clusters (simple controls)
            if len(st.session_state.manual_clusters) > 0:
                for ck in list(st.session_state.manual_clusters.keys()):
                    cdat = st.session_state.manual_clusters[ck]
                    with st.expander(f"{ck} — {len(cdat.get('members', []))} usaha", expanded=False):
                        show_ck = st.checkbox("Tampilkan di peta radius", value=cdat.get('active', True), key=f"rad_active_{ck}")
                        st.session_state.manual_clusters[ck]['active'] = show_ck
                        # allow removing members that are not in current radius (but keep them)
                        edit_members = st.multiselect("Edit anggota (visible in filtered list)", choices_radius, default=[m for m in cdat.get('members', []) if m in choices_radius], key=f"rad_members_{ck}")
                        # update only those in current radius selection to avoid accidental removal of external members
                        # merge: keep non-visible members + selected visible members
                        nonvis = [m for m in cdat.get('members', []) if m not in choices_radius]
                        st.session_state.manual_clusters[ck]['members'] = nonvis + edit_members
                        newcol = st.color_picker("Warna cluster", value=cdat.get('color', '#22c55e'), key=f"rad_color_{ck}")
                        st.session_state.manual_clusters[ck]['color'] = newcol
                        if st.button("Hapus Cluster", key=f"rad_del_{ck}"):
                            del st.session_state.manual_clusters[ck]
                            st.experimental_rerun()

            # Render manual clusters on this radius map (only show members that are inside in_radius)
            for cname, cdata in st.session_state.manual_clusters.items():
                if not cdata.get('active', True):
                    continue
                # collect points that are inside current radius
                pts = []
                for nm in cdata.get('members', []):
                    rowr = in_radius[in_radius["nama_usaha"] == nm]
                    if rowr.shape[0] >= 1:
                        rr = rowr.iloc[0]
                        pts.append((rr['lon'], rr['lat']))  
                # shapely uses (x, y) => (lon, lat)
                if len(pts) >= 3 and SHAPELY_AVAILABLE:
                    poly = MultiPoint(pts).convex_hull
                    coords = [(y, x) for x, y in poly.exterior.coords]
                    folium.Polygon(coords, color=cdata.get('color', '#22c55e'), weight=2, fill=True, fill_color=cdata.get('color', '#22c55e'), fill_opacity=0.3, popup=f"{cname}").add_to(m)
                    # add cluster label at centroid
                    try:
                        cx, cy = poly.centroid.x, poly.centroid.y
                        folium.map.Marker([cy, cx], icon=folium.DivIcon(html=f"<div style='font-weight:700;padding:2px 6px;background:rgba(255,255,255,0.8);border-radius:4px'>{cname}</div>")).add_to(m)
                    except Exception:
                        pass
                elif len(pts) > 0:
                    # fallback: draw small buffered circles around points and combine visually
                    for lon, lat in pts:
                        folium.CircleMarker(location=[lat, lon], radius=8, color=cdata.get('color', '#22c55e'), fill=True, fill_color=cdata.get('color', '#22c55e'), fill_opacity=0.6, popup=f"{cname}").add_to(m)

            st_folium(m, width=980, height=600)
            st.markdown("</div>", unsafe_allow_html=True)

    with colR:

        # Tabel Usaha dengan Review Terbesar
        # ================================
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.write("### Usaha dengan Jumlah Review Terbanyak")

        # Urutkan usaha berdasarkan jumlah review
        df_review_top = df_filtered.sort_values("review", ascending=False).head(10)

        # Styling tabel agar lebih premium
        st.dataframe(
            df_review_top[["nama_usaha", "Jenis Usaha", "review"]]
            .rename(columns={
                "nama_usaha": "Nama Usaha",
                "Jenis Usaha": "Jenis Usaha",
                "review": "Jumlah Review",
            }),
            use_container_width=True,
            hide_index=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.write("### Daftar Usaha Dalam Radius")
        if center_choice == "-- PILIH --":
            st.info("Pilih titik pusat untuk melihat daftar.")
        else:
            t = in_radius[["nama_usaha", "Jenis Usaha", "daerah", "jarak_m", "review"]].copy()
            t["jarak_m"] = t["jarak_m"].astype(int)
            st.dataframe(t.sort_values("jarak_m").reset_index(drop=True), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Add note interface
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.write("### Buat Catatan Kunjungan")
        if center_choice == "-- PILIH --":
            st.info("Pilih titik pusat untuk menyimpan catatan terkait titik tersebut.")
        else:
            nama = st.selectbox("Pilih Usaha", in_radius["nama_usaha"].tolist())
            catatan = st.text_area("Catatan", placeholder="Tulis catatan kunjungan, outcome, follow-up...")
            if st.button("Simpan Catatan"):
                ensure_notes_file()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                lat = in_radius[in_radius["nama_usaha"]==nama]["lat"].iloc[0]
                lon = in_radius[in_radius["nama_usaha"]==nama]["lon"].iloc[0]
                new = {"timestamp":now, "nama_usaha":nama, "lat":lat, "lon":lon, "catatan":catatan}
                nd = pd.read_csv(NOTES_PATH) if os.path.exists(NOTES_PATH) else pd.DataFrame(columns=["timestamp","nama_usaha","lat","lon","catatan"])
                nd = pd.concat([nd, pd.DataFrame([new])], ignore_index=True)
                nd.to_csv(NOTES_PATH, index=False)
                st.success("Catatan tersimpan.")
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Peta Cluster":
        left_col, right_col = st.columns([2,1])
        with left_col:
            st.write("### Peta Segmentasi Cluster Usaha")
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            if len(df_filtered) == 0:
                st.info("Tidak ada usaha yang cocok dengan filter.")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                center_lat = df_filtered["lat"].median()
                center_lon = df_filtered["lon"].median()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB positron")
                mc = MarkerCluster()
                for _, r in df_filtered.iterrows():
                    folium.Marker(
                        [r["lat"], r["lon"]],
                        popup=f"<b>{r['nama_usaha']}</b><br>{r['Jenis Usaha']}<br>{r['daerah']}<br>Review: {int(r['review'])}"
                    ).add_to(mc)
                mc.add_to(m)
                # ================================
# 🔷 Render ALL Manual Clusters
# ================================
                if "manual_clusters" in st.session_state and SHAPELY_AVAILABLE:

                    for cname, cdata in st.session_state.manual_clusters.items():

                        if not cdata.get("active", True):
                            continue

                        points = []

                        for usaha in cdata.get("members", []):
                            row = data[data["nama_usaha"] == usaha]
                            if not row.empty:
                                r = row.iloc[0]
                                points.append((r["lon"], r["lat"]))  # (x,y)

                        if len(points) >= 3:
                            poly = MultiPoint(points).convex_hull
                            coords = [(lat, lon) for lon, lat in poly.exterior.coords]

                            folium.Polygon(
                                locations=coords,
                                color=cdata.get("color", "#22c55e"),
                                weight=3,
                                fill=True,
                                fill_color=cdata.get("color", "#22c55e"),
                                fill_opacity=0.25,
                                tooltip=f"Cluster: {cname}"
                            ).add_to(m)

                            # Label cluster di centroid
                            cx, cy = poly.centroid.x, poly.centroid.y
                            folium.Marker(
                                [cy, cx],
                                icon=folium.DivIcon(html=f"""
                                    <div style="
                                        font-weight:700;
                                        background:rgba(255,255,255,0.85);
                                        color:white;
                                        padding:4px 8px;
                                        border-radius:6px;
                                        font-size:11px;
                                        box-shadow:0 2px 6px rgba(0,0,0,0.3);">
                                        {cname}
                                    </div>
                                """)
                            ).add_to(m)

                st_folium(m, width=1000, height=900)
                st.markdown("</div>", unsafe_allow_html=True)


elif page == "Data & Catatan":
    st.write("### Data & Catatan (Eksport / Import)")
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.write("#### Data Usaha (Preview)")
    st.dataframe(data.head(200), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.write("#### Catatan Kunjungan")
    nd = pd.read_csv(NOTES_PATH) if os.path.exists(NOTES_PATH) else pd.DataFrame(columns=["timestamp","nama_usaha","lat","lon","catatan"])
    st.dataframe(nd.sort_values("timestamp", ascending=False).reset_index(drop=True), use_container_width=True)
    csv = nd.to_csv(index=False).encode('utf-8')
    st.download_button("Download Catatan CSV", csv, "catatan_kunjungan.csv", "text/csv")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.write("#### Import Data Baru (Replace)")
    uploaded = st.file_uploader("Upload CSV (akan mengganti data saat ini)", type=["csv"])
    if uploaded is not None:
        try:
            newdf = pd.read_csv(uploaded)
            newdf.to_csv(DATA_PATH, index=False)
            st.success("Data baru diupload. Dashboard akan reload otomatis.")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Gagal mengupload: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Settings":
    st.write("### Settings & Preferences")
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.write("Auto-refresh file change:")
    st.checkbox("Enable Auto Reload on CSV change", value=AUTO_REFRESH, key="auto_reload_checkbox")
    if st.button("Force Check & Reload"):
        st.session_state.data_mtime = file_mtime(DATA_PATH)
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)
# -------------------------
# Footer / small helper
# -------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div style='opacity:0.6;font-size:12px'>Built with ❤️ — Ultra-Premium Dashboard · Local mode</div>", unsafe_allow_html=True)



