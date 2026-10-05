import os
import h5py
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# ==============================================================================
# 1. EXTRAER VARIABLES DE ARCHIVOS .H5 (SOLO IS_EDGE == FALSE)
# ==============================================================================
def extract_all_h5_data(folder_path):
    """
    Recorre la carpeta principal y TODAS sus subcarpetas (recursivamente)
    extrayendo variables numéricas de archivos .h5 donde is_edge == False.
    """
    all_records = []
    
    # os.walk recorre la carpeta raíz y cualquier subcarpeta
    h5_filepaths = []
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            if f.endswith('.h5'):
                h5_filepaths.append(os.path.join(dirpath, f))
                
    if not h5_filepaths:
        raise FileNotFoundError(f"No se encontraron archivos .h5 en '{folder_path}' ni en sus subcarpetas.")
        
    for fpath in sorted(h5_filepaths):
        filename = os.path.basename(fpath)
        sample_name = os.path.splitext(filename)[0]
        
        with h5py.File(fpath, 'r') as f:
            if "contours" not in f:
                continue
            grp = f["contours"]
            for key in grp.keys():
                item = grp[key]
                attrs = dict(item.attrs) if hasattr(item, 'attrs') else {}
                
                # --- FILTRO ESTRICTO IS_EDGE == FALSE ---
                is_edge_val = attrs.get("is_edge", False)
                if isinstance(is_edge_val, (np.ndarray, list)):
                    is_edge_val = is_edge_val[0] if len(is_edge_val) > 0 else False
                
                if bool(is_edge_val):
                    continue  # Se ignora si toca el borde
                    
                rec = {'Muestra': sample_name, 'Contour_ID': key, 'Ruta_Archivo': fpath}
                
                # Extraer numéricos de atributos
                for k, v in attrs.items():
                    if k == 'is_edge':
                        continue
                    if isinstance(v, (int, float, np.number)) and not isinstance(v, (bool, np.bool_)):
                        rec[k] = float(v)
                    elif isinstance(v, np.ndarray) and v.size == 1 and np.issubdtype(v.dtype, np.number):
                        rec[k] = float(v.item())
                        
                # Extraer numéricos de sub-datasets escalares
                if isinstance(item, h5py.Group):
                    for subk in item.keys():
                        sub_item = item[subk]
                        if isinstance(sub_item, h5py.Dataset) and sub_item.shape in [(), (1,)]:
                            val = sub_item[()]
                            if isinstance(val, (int, float, np.number)) and not isinstance(val, (bool, np.bool_)):
                                rec[subk] = float(val)
                                
                # Variables derivadas
                if 'shape_score' not in rec and 'area' in rec and 'perimeter' in rec:
                    if rec['perimeter'] > 0:
                        rec['shape_score'] = (4 * np.pi * rec['area']) / (rec['perimeter'] ** 2)
                if 'irregularity' not in rec and 'shape_score' in rec and 'convex_shape' in rec:
                    if rec['convex_shape'] > 0:
                        rec['irregularity'] = float(np.arctan(rec['shape_score'] / rec['convex_shape']))
                        
                all_records.append(rec)
                
    return pd.DataFrame(all_records)

# ==============================================================================
# 2. ANÁLISIS ESTADÍSTICO MULTIVARIADO (HOTELLING T^2 + RANDOM FOREST)
# ==============================================================================
def run_multivariate_analysis(df, sample_col='Muestra'):
    """
    Ejecuta el test T^2 de Hotelling (p-dimensional) y entrena un modelo Random Forest
    para obtener el ranking de importancia y el tamaño del efecto (d de Cohen).
    """
    ignore_cols = [sample_col, 'Contour_ID']
    feature_cols = [c for c in df.columns if c not in ignore_cols and pd.api.types.is_numeric_dtype(df[c])]
    
    samples = df[sample_col].unique()
    if len(samples) < 2:
        raise ValueError("Se requieren al menos 2 muestras para comparar multivariadamente.")
        
    s1_name, s2_name = samples[0], samples[1]
    
    df1 = df[df[sample_col] == s1_name].dropna(subset=feature_cols)
    df2 = df[df[sample_col] == s2_name].dropna(subset=feature_cols)
    
    X1 = df1[feature_cols].values
    X2 = df2[feature_cols].values
    
    n1, p = X1.shape
    n2, _ = X2.shape
    
    # 1. Hotelling T^2 Multivariado
    m1, m2 = np.mean(X1, axis=0), np.mean(X2, axis=0)
    diff = m1 - m2
    S1 = np.cov(X1, rowvar=False, ddof=1)
    S2 = np.cov(X2, rowvar=False, ddof=1)
    S_pooled = ((n1 - 1) * S1 + (n2 - 1) * S2) / (n1 + n2 - 2)
    S_inv = np.linalg.pinv(S_pooled)
    
    T2 = (n1 * n2 / (n1 + n2)) * float(np.dot(diff, np.dot(S_inv, diff)))
    D_M = float(np.sqrt(max(0, np.dot(diff, np.dot(S_inv, diff)))))
    
    df1_f = p
    df2_f = n1 + n2 - p - 1
    F_stat = ((df2_f) / (p * (n1 + n2 - 2))) * T2 if df2_f > 0 else np.nan
    p_val_hotelling = float(stats.f.sf(F_stat, df1_f, df2_f)) if not np.isnan(F_stat) else np.nan
    
    # 2. Random Forest Classifier para Importancia y Separabilidad
    X = np.vstack([X1, X2])
    y = np.array([0]*n1 + [1]*n2)
    rf = RandomForestClassifier(n_estimators=200, random_state=42, oob_score=True)
    rf.fit(X, y)
    
    oob_preds = rf.oob_decision_function_[:, 1]
    auc_score = float(roc_auc_score(y, oob_preds))
    importances = rf.feature_importances_ * 100.0
    
    # 3. Cohen's d e Índices Individuales
    rank_records = []
    for i, col in enumerate(feature_cols):
        mean1, std1 = df1[col].mean(), df1[col].std(ddof=1)
        mean2, std2 = df2[col].mean(), df2[col].std(ddof=1)
        
        s_p = np.sqrt(((n1 - 1)*(std1**2) + (n2 - 1)*(std2**2)) / (n1 + n2 - 2))
        cohen_d = abs(mean1 - mean2) / s_p if s_p > 0 else 0.0
        
        rank_records.append({
            'Variable': col,
            'Importancia RF (%)': importances[i],
            'Tamaño Efecto (d de Cohen)': cohen_d,
            f'Media ({s1_name})': mean1,
            f'DE ({s1_name})': std1,
            f'Media ({s2_name})': mean2,
            f'DE ({s2_name})': std2
        })
        
    rank_df = pd.DataFrame(rank_records).sort_values(by='Importancia RF (%)', ascending=False).reset_index(drop=True)
    rank_df.insert(0, 'Ranking', rank_df.index + 1)
    
    summary_data = {
        'Muestra 1': s1_name,
        'Muestra 2': s2_name,
        'N1 (is_edge=False)': n1,
        'N2 (is_edge=False)': n2,
        'Variables Analizadas (p)': p,
        'Dist. Mahalanobis (D_M)': D_M,
        'Hotelling T^2': T2,
        'F-Estadístico': F_stat,
        'p-valor (Hotelling)': p_val_hotelling,
        'Diferencia Multivariada': 'Sí (p < 0.05)' if p_val_hotelling < 0.05 else 'No Significativa',
        'RF AUC-ROC (OOB Score)': auc_score
    }
    
    return summary_data, rank_df

# ==============================================================================
# 3. GUARDAR NUEVA PESTAÑA EN EL EXCEL EXISTENTE
# ==============================================================================
def add_multivariate_tab_to_excel(excel_path, summary_dict, rank_df, sheet_name="Análisis Multivariado Global"):
    """
    Añade la pestaña 'Análisis Multivariado Global' al archivo Excel sin borrar las existentes.
    """
    if os.path.exists(excel_path):
        wb = openpyxl.load_workbook(excel_path)
    else:
        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])
            
    if sheet_name in wb.sheetnames:
        wb.remove(wb[sheet_name])
        
    ws = wb.create_sheet(title=sheet_name)
    
    # Estilos
    fill_header = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    font_title = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    font_section = Font(name="Calibri", size=11, bold=True, color="1F4E79")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    
    border_thin = Border(
        left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
    )
    
    # Encabezado
    ws.cell(row=1, column=1, value="ANÁLISIS ESTADÍSTICO NO PARAMÉTRICO Y MULTIVARIADO (p VARIABLES)").font = font_title
    ws.cell(row=2, column=1, value="Filtro estricto aplicado: is_edge = False (poros completos en interior)").font = Font(italic=True, size=10, color="595959")
    
    # Tabla 1: Resumen Global
    ws.cell(row=4, column=1, value="1. Resumen de Pruebas Multivariadas Globales").font = font_section
    summary_df = pd.DataFrame([summary_dict])
    start_r = 5
    
    for r_idx, row in enumerate(dataframe_to_rows(summary_df, index=False, header=True), start=start_r):
        ws.append(row)
        for c_idx in range(1, len(row) + 1):
            cell = ws.cell(row=ws.max_row, column=c_idx)
            cell.border = border_thin
            if r_idx == start_r:
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.font = font_regular
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if isinstance(cell.value, float):
                    cell.value = round(cell.value, 6) if abs(cell.value) < 0.001 else round(cell.value, 4)
                    
    # Tabla 2: Ranking de Variables
    start_r_rank = ws.max_row + 3
    ws.cell(row=start_r_rank, column=1, value="2. Ranking de Contribución por Variable (Random Forest + Cohen's d)").font = font_section
    header_row_idx = start_r_rank + 1
    
    for r_idx, row in enumerate(dataframe_to_rows(rank_df, index=False, header=True), start=header_row_idx):
        ws.append(row)
        curr_row = ws.max_row
        for c_idx in range(1, len(row) + 1):
            cell = ws.cell(row=curr_row, column=c_idx)
            cell.border = border_thin
            if r_idx == header_row_idx:
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.font = font_regular
                if c_idx == 1:
                    cell.alignment = Alignment(horizontal="center")
                    cell.font = font_bold
                elif c_idx == 2:
                    cell.alignment = Alignment(horizontal="left")
                    cell.font = font_bold
                else:
                    cell.alignment = Alignment(horizontal="right")
                    if isinstance(cell.value, float):
                        cell.value = round(cell.value, 4)

    # Ajustar ancho de columnas
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
        
    wb.save(excel_path)

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    CARPETA_H5 = "H:\\Otros ordenadores\\Microscopio\\Silvia EEUU\\Porosidad de los mosaicos 4"  # Ruta donde están tus archivos .h5
    EXCEL_SALIDA = "Reporte_Morfometrico_Completo.xlsx"  # Archivo Excel de salida
    
    # 1. Extraer datos ignorando bordes
    df_poros = extract_all_h5_data(CARPETA_H5)
    print(f"Poros procesados (is_edge=False): {len(df_poros)}")
    
    # 2. Ejecutar análisis multivariado p-dimensional
    summary_dict, ranking_df = run_multivariate_analysis(df_poros)
    
    # 3. Añadir la pestaña al Excel
    add_multivariate_tab_to_excel(EXCEL_SALIDA, summary_dict, ranking_df)
    print(f"¡Análisis multivariado completado y guardado en la pestaña 'Análisis Multivariado Global' de '{EXCEL_SALIDA}'!")