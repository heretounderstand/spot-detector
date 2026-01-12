import streamlit as st
import pandas as pd
import re
from database import Database
from models import Spot, Enregistrement
from detector_v2 import SpotDetector
from excel_report import ExcelReportGenerator
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="🔍 Détecteur de Spots",
    page_icon="🎙️",
    layout="wide"
)

db = Database()

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; padding: 0 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🔍 Détecteur de Spots Publicitaires")

stats = db.get_stats()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🎯 Spots", stats['nb_spots'])
with col2:
    st.metric("📹 Enregistrements", stats['nb_enregistrements'])
with col3:
    st.metric("✅ Détections", stats['nb_detections'])
with col4:
    st.metric("📊 Confiance", f"{stats['avg_confidence']:.1f}%" if stats['nb_detections'] > 0 else "N/A")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Importer", "🔍 Analyser", "📊 Rapports", "📺 Chaînes", "⚙️ Gérer"])

# ==================== ONGLET 1: IMPORTER ====================
with tab1:
    st.header("📤 Importer SRT")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎬 Spots")
        spot_files = st.file_uploader(
            "Fichiers SRT des spots",
            type=["srt"],
            accept_multiple_files=True,
            key="spot_upload"
        )
        
        if st.button("💾 Enregistrer Spots", disabled=not spot_files):
            with st.spinner("Importation..."):
                added = 0
                for file in spot_files:
                    content = file.read().decode("utf-8")
                    spot = Spot.from_filename(file.name, content)
                    spot_id = db.add_spot(spot)
                    if spot_id:
                        added += 1
                st.success(f"✅ {added} spot(s) importé(s)")
                st.rerun()
    
    with col2:
        st.subheader("📹 Enregistrements")
        rec_files = st.file_uploader(
            "Fichiers SRT des enregistrements",
            type=["srt"],
            accept_multiple_files=True,
            key="rec_upload",
            help="Format: CHAINE_YYYY-MM-DD_HH-MM-SS_HH-MM-SS.srt"
        )
        
        if st.button("💾 Enregistrer Enregistrements", disabled=not rec_files):
            with st.spinner("Importation..."):
                added = 0
                skipped = 0
                for file in rec_files:
                    content = file.read().decode("utf-8")
                    # Utiliser chaine_id comme nom par défaut
                    pattern = r'^([^_]+)_'
                    match = re.match(pattern, file.name)
                    if match:
                        chaine_id = match.group(1)
                        enreg = Enregistrement.from_filename(file.name, content, chaine_id)
                        if enreg:
                            enreg_id = db.add_enregistrement(enreg)
                            if enreg_id:
                                added += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1
                
                if added > 0:
                    st.success(f"✅ {added} enregistrement(s) importé(s)")
                if skipped > 0:
                    st.warning(f"⚠️ {skipped} fichier(s) ignoré(s)")
                st.rerun()

# ==================== ONGLET 2: ANALYSER ====================
with tab2:
    st.header("🔍 Analyser Spots")
    
    all_spots = db.get_all_spots()
    all_enregs = db.get_all_enregistrements()
    
    if not all_spots:
        st.warning("⚠️ Aucun spot disponible. Importez des spots dans l'onglet 'Importer'.")
    elif not all_enregs:
        st.warning("⚠️ Aucun enregistrement disponible.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Sélection")
            
            spot_options = {s.nom_campagne: s.id for s in all_spots}
            selected_spots = st.multiselect(
                "Spots à analyser",
                options=list(spot_options.keys()),
                default=list(spot_options.keys())[:1]
            )
            
            all_chaines_tuples = db.get_all_chaines()
            chaine_display = {f"{nom} ({cid})": cid for cid, nom in all_chaines_tuples}
            selected_chaines_display = st.multiselect(
                "Chaînes",
                options=list(chaine_display.keys()),
                default=list(chaine_display.keys())
            )
            selected_chaines = [chaine_display[d] for d in selected_chaines_display]
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                date_min = min(e.date_enreg for e in all_enregs)
                date_debut = st.date_input("Du", value=datetime.fromisoformat(date_min))
            with col_d2:
                date_max = max(e.date_enreg for e in all_enregs)
                date_fin = st.date_input("Au", value=datetime.fromisoformat(date_max))
        
        with col2:
            st.subheader("Lancer l'analyse")
            
            if st.button("🚀 Analyser", type="primary", use_container_width=True):
                if not selected_spots:
                    st.error("Sélectionnez au moins un spot")
                else:
                    filtered_enregs = db.get_enregistrements_by_filters(
                        chaine_ids=selected_chaines if selected_chaines else None,
                        date_debut=str(date_debut),
                        date_fin=str(date_fin)
                    )
                    
                    if not filtered_enregs:
                        st.warning("Aucun enregistrement ne correspond aux filtres")
                    else:
                        progress = st.progress(0)
                        status = st.empty()
                        
                        detector = SpotDetector()
                        total_detections = 0
                        
                        for idx, spot_name in enumerate(selected_spots):
                            spot_id = spot_options[spot_name]
                            spot = db.get_spot_by_id(spot_id)
                            
                            status.text(f"Analyse: {spot_name} ({idx+1}/{len(selected_spots)})")
                            
                            # Inclure heure_debut dans les données d'enregistrement
                            enreg_data = [(e.id, e.contenu_srt, e.heure_debut) for e in filtered_enregs]
                            detections = detector.detect_spot_in_enregistrements(
                                spot_id,
                                spot.contenu_srt,
                                enreg_data
                            )
                            
                            for det in detections:
                                db.add_detection(det)
                            
                            total_detections += len(detections)
                            progress.progress((idx + 1) / len(selected_spots))
                        
                        progress.empty()
                        status.empty()
                        st.success(f"✅ Analyse terminée: {total_detections} détection(s)")
                        st.rerun()

# ==================== ONGLET 3: RAPPORTS ====================
with tab3:
    st.header("📊 Rapports et Visualisations")
    
    with st.expander("🔧 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            all_spots_rapport = db.get_all_spots()
            spot_filter = st.multiselect(
                "Spots",
                options=[s.nom_campagne for s in all_spots_rapport],
                key="rapport_spots"
            )
        
        with col2:
            all_chaines_tuples_r = db.get_all_chaines()
            chaine_display_r = {f"{nom} ({cid})": cid for cid, nom in all_chaines_tuples_r}
            chaines_filter_display = st.multiselect(
                "Chaînes",
                options=list(chaine_display_r.keys()),
                key="rapport_chaines"
            )
            chaines_filter = [chaine_display_r[d] for d in chaines_filter_display]
        
        with col3:
            all_enregs_rapport = db.get_all_enregistrements()
            if all_enregs_rapport:
                date_min_r = min(e.date_enreg for e in all_enregs_rapport)
                date_max_r = max(e.date_enreg for e in all_enregs_rapport)
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    date_debut_r = st.date_input("Du", value=datetime.fromisoformat(date_min_r), key="date_deb_r")
                with col_r2:
                    date_fin_r = st.date_input("Au", value=datetime.fromisoformat(date_max_r), key="date_fin_r")
    
    spot_ids_filter = [s.id for s in all_spots_rapport if s.nom_campagne in spot_filter] if spot_filter else None
    
    detections = db.get_detections_enriched(
        spot_ids=spot_ids_filter,
        chaine_ids=chaines_filter if chaines_filter else None,
        date_debut=str(date_debut_r) if all_enregs_rapport else None,
        date_fin=str(date_fin_r) if all_enregs_rapport else None
    )
    
    if not detections:
        st.info("📭 Aucune détection à afficher")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎯 Détections", len(detections))
        with col2:
            spots_uniques = len(set(d.spot_nom for d in detections))
            st.metric("🎬 Spots uniques", spots_uniques)
        with col3:
            avg_conf = sum(d.confidence for d in detections) / len(detections)
            st.metric("📊 Confiance moy.", f"{avg_conf:.1f}%")
        
        st.markdown("---")
        
        st.subheader("📋 Détails")
        df_data = []
        for d in detections:
            df_data.append({
                "Spot": d.spot_nom,
                "Chaîne": d.enreg_chaine_nom,
                "Date": d.enreg_date,
                "Début": d.start_time,
                "Fin": d.end_time,
                "Durée": f"{(d.end_seconds - d.start_seconds):.1f}s",
                "Type": "✅ EXACT" if d.match_type == "exact" else "🔀 FUZZY",
                "Confiance": f"{d.confidence:.1f}%"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("💾 Exporter")
        
        if st.button("📥 Générer Rapport Excel", use_container_width=True):
            with st.spinner("Génération du rapport..."):
                temp_path = "/tmp/rapport_spots.xlsx"
                ExcelReportGenerator.generate_report(detections, temp_path)
                
                with open(temp_path, "rb") as f:
                    excel_data = f.read()
                
                st.download_button(
                    label="📥 Télécharger Rapport Excel",
                    data=excel_data,
                    file_name=f"rapport_spots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# ==================== ONGLET 4: CHAÎNES ====================
with tab4:
    st.header("📺 Gestion des Chaînes")
    
    all_chaines = db.get_all_chaines()
    
    if not all_chaines:
        st.info("Aucune chaîne. Importez des enregistrements pour créer des chaînes.")
    else:
        st.subheader("Renommer les chaînes")
        
        for chaine_id, chaine_nom in all_chaines:
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.code(chaine_id)
            
            with col2:
                new_name = st.text_input(
                    "Nom",
                    value=chaine_nom,
                    key=f"rename_{chaine_id}",
                    label_visibility="collapsed"
                )
            
            with col3:
                if st.button("💾 Sauver", key=f"save_{chaine_id}"):
                    if new_name and new_name != chaine_nom:
                        db.update_chaine_nom(chaine_id, new_name)
                        st.success("✅ Mis à jour")
                        st.rerun()

# ==================== ONGLET 5: GÉRER ====================
with tab5:
    st.header("⚙️ Gestion des Données")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎬 Spots")
        spots_list = db.get_all_spots()
        
        if spots_list:
            for spot in spots_list:
                col_s1, col_s2 = st.columns([3, 1])
                with col_s1:
                    st.text(f"📌 {spot.nom_campagne}")
                with col_s2:
                    if st.button("🗑️", key=f"del_spot_{spot.id}"):
                        db.delete_spot(spot.id)
                        st.rerun()
        else:
            st.info("Aucun spot")
    
    with col2:
        st.subheader("📹 Enregistrements")
        enregs_list = db.get_all_enregistrements()
        
        if enregs_list:
            for enreg in enregs_list[:20]:
                col_e1, col_e2 = st.columns([3, 1])
                with col_e1:
                    st.text(f"📺 {enreg.chaine_nom} - {enreg.date_enreg}")
                with col_e2:
                    if st.button("🗑️", key=f"del_enreg_{enreg.id}"):
                        db.delete_enregistrement(enreg.id)
                        st.rerun()
            
            if len(enregs_list) > 20:
                st.caption(f"... et {len(enregs_list) - 20} autres")
        else:
            st.info("Aucun enregistrement")
