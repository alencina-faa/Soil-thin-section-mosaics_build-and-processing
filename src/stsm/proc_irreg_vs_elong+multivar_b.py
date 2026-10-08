"""
Pore Morphology and Multivariate Analysis Pipeline
===================================================
This script processes HDF5 (.h5 / .hdf5) files containing pore morphological data extracted from 
microscopy mosaic images. It filters interior pores (is_edge == False, is_over_50um == True) 
and performs statistical comparative analyses across multiple sample groups.

Main Features:
1. Data Extraction & Preprocessing:
   - Reads HDF5 files and extracts pore metrics.
   - Converts irregularity from degrees (pore_irregularity_deg) to radians (irregularity_rad).
   - Extracts pore elongation (pore_elongation) and dimensional metrics.

2. Bivariate Analysis (2D Kolmogorov-Smirnov Test & 2D KDE Plots):
   - Computes 2D Kolmogorov-Smirnov (K-S 2D) statistics to evaluate pairwise sample 
     differences between Irregularity (in radians) and Elongation (pore_elongation).
   - Generates 2D Kernel Density Estimation (KDE) maps for each sample.
   - Exported to the Excel sheet: "Prueba K-S 2D" (including table and 1/4 scaled 2D KDE plot mosaic).

3. Global Multivariate Analysis:
   - Uses a Random Forest Classifier with Out-of-Bag (OOB) scoring to quantify multivariate 
     separability across sample pairs.
   - Computes Permutation Feature Importance based on ROC-AUC drop to identify key morphometric 
     descriptors driving pairwise sample differences.
   - Exported to the Excel sheet: "Análisis Multivariado Global".
"""

import math
import os
import h5py
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import seaborn as sns
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score


# ==========================================
# 1. HDF5 FILE READING AND EXTRACTION
# ==========================================
def process_h5_file(file_path):
    """
    Reads an HDF5 (.h5 / .hdf5) file, extracts interior pore attributes (is_edge == False),
    and converts pore irregularity from degrees to radians.
    """
    data = []

    try:
        with h5py.File(file_path, "r") as f:
            if "contours" not in f:
                return None

            contours_group = f["contours"]

            for contour_id, group in contours_group.items():
                # Filter interior contours only (is_edge == False)
                is_edge_value = np.asarray(group.attrs.get("is_edge", True))
                is_edge = bool(is_edge_value.reshape(-1)[0]) if is_edge_value.size else False
                if is_edge:
                    continue

                is_over_50um_value = np.asarray(group.attrs.get("is_over_50um", False))
                is_over_50um = (
                    bool(is_over_50um_value.reshape(-1)[0]) if is_over_50um_value.size else False
                )
                
                record = {
                    "Contour_ID": contour_id,
                    "is_edge": is_edge,
                    "is_over_50um": is_over_50um,
                }

                # Extract scalar attributes
                for key, value in group.attrs.items():
                    if key in {"is_edge", "is_over_50um"}:
                        continue
                    scalar = np.asarray(value)
                    if scalar.size == 1 and np.issubdtype(scalar.dtype, np.number):
                        record[key] = float(scalar.item())

                # Extract scalar datasets inside contour group
                if isinstance(group, h5py.Group):
                    for key, item in group.items():
                        if isinstance(item, h5py.Dataset) and item.shape in [(), (1,)]:
                            value = np.asarray(item[()])
                            if value.size == 1 and np.issubdtype(value.dtype, np.number) and not np.issubdtype(value.dtype, np.bool_):
                                record[key] = float(value.item())

                # Compute shape_score if missing but area and perimeter exist
                shape = record.get("shape_score")
                if shape is None and "area" in record and "perimeter" in record and record["perimeter"] > 0:
                    shape = 4.0 * math.pi * record["area"] / record["perimeter"] ** 2
                    record["shape_score"] = shape

                convex_shape = record.get("convex_shape")

                # Convert irregularity to radians (from pore_irregularity_deg or shape/convex_shape ratio)
                if "pore_irregularity_deg" in record and record["pore_irregularity_deg"] is not None:
                    record["irregularity_rad"] = math.radians(record["pore_irregularity_deg"])
                elif shape is not None and convex_shape is not None and convex_shape != 0:
                    record["irregularity_rad"] = math.atan(float(shape) / float(convex_shape))

                data.append(record)

    except Exception as e:
        print(f"Error reading {os.path.basename(file_path)}: {str(e)}")
        return None

    if not data:
        return None

    df = pd.DataFrame(data)
    return df


# ==========================================
# 2. GLOBAL MULTIVARIATE ANALYSIS (RANDOM FOREST)
# ==========================================
def run_multivariate_analysis(df, sample_col="Muestra"):
    """
    Compares all sample pairs in p dimensions using Random Forest Classification 
    (OOB ROC-AUC) and ROC-AUC drop Permutation Feature Importance.
    """
    candidate_features = [
        "area",
        "convex_shape",
        "ellipse_angle_deg",
        "perimeter",
        "pore_elongation",
        "pore_irregularity_deg",
        "shape_score",
    ]
    feature_cols = [c for c in candidate_features if c in df.columns]
    if not feature_cols:
        ignore_cols = {sample_col, "Contour_ID", "is_edge", "is_over_50um", "irregularity_rad"}
        feature_cols = sorted([c for c in df.columns if c not in ignore_cols and pd.api.types.is_numeric_dtype(df[c])])

    # Filter eligible rows (is_edge == False & is_over_50um == True)
    eligible_mask = pd.Series(True, index=df.index)
    if "is_edge" in df.columns:
        eligible_mask &= df["is_edge"].eq(False)
    if "is_over_50um" in df.columns:
        eligible_mask &= df["is_over_50um"].eq(True)

    eligible_df = df.loc[eligible_mask].copy()
    features = eligible_df[feature_cols].replace([np.inf, -np.inf], np.nan)
    samples = eligible_df[sample_col].dropna().unique()

    if len(samples) < 2:
        raise ValueError(
            "At least 2 samples with is_edge=False and is_over_50um=True are required for multivariate analysis."
        )

    summary_records = []
    ranking_records = []

    for sample1_index, sample1_name in enumerate(samples[:-1]):
        for sample2_name in samples[sample1_index + 1:]:
            sample1_mask = eligible_df[sample_col] == sample1_name
            sample2_mask = eligible_df[sample_col] == sample2_name
            sample1 = features.loc[sample1_mask].dropna(subset=feature_cols)
            sample2 = features.loc[sample2_mask].dropna(subset=feature_cols)
            values1 = sample1[feature_cols].to_numpy(dtype=float)
            values2 = sample2[feature_cols].to_numpy(dtype=float)
            n1, n2 = len(values1), len(values2)
            feature_count = len(feature_cols)

            summary = {
                "Muestra 1": sample1_name,
                "Muestra 2": sample2_name,
                "N1 (condiciones aplicadas)": n1,
                "N2 (condiciones aplicadas)": n2,
                "Variables Analizadas (p)": feature_count,
                "RF AUC-ROC (OOB Score)": np.nan,
            }

            if n1 < 2 or n2 < 2:
                summary_records.append(summary)
                continue

            # Train Random Forest Classifier
            values = np.vstack([values1, values2])
            labels = np.array([0] * n1 + [1] * n2)
            classifier = RandomForestClassifier(n_estimators=200, random_state=42, oob_score=True)
            classifier.fit(values, labels)

            # Evaluate Out-of-Bag (OOB) ROC-AUC score
            oob_predictions = classifier.oob_decision_function_[:, 1]
            valid_predictions = np.isfinite(oob_predictions)
            auc_score = (
                float(roc_auc_score(labels[valid_predictions], oob_predictions[valid_predictions]))
                if valid_predictions.sum() > 1 and len(np.unique(labels[valid_predictions])) == 2
                else np.nan
            )

            # Compute Permutation Feature Importance based on ROC-AUC reduction
            perm_res = permutation_importance(
                classifier, values, labels,
                scoring='roc_auc',
                n_repeats=10,
                random_state=42
            )
            drop_auc_mean = perm_res.importances_mean
            drop_auc_clipped = np.maximum(0, drop_auc_mean)
            if drop_auc_clipped.sum() > 0:
                importances_pct = (drop_auc_clipped / drop_auc_clipped.sum()) * 100.0
            else:
                importances_pct = np.zeros_like(drop_auc_clipped)

            summary["RF AUC-ROC (OOB Score)"] = auc_score
            summary_records.append(summary)

            # Store ranking records for the pivot matrix
            for index, column in enumerate(feature_cols):
                ranking_records.append({
                    "Muestra 1": sample1_name,
                    "Muestra 2": sample2_name,
                    "Variable": column,
                    "Importancia Permutación RF (%)": importances_pct[index]
                })

    # Create Pivoted Matrix (Variables in rows, Sample pairs in columns)
    ranking_df = pd.DataFrame(ranking_records)
    if not ranking_df.empty:
        pivot_matrix_df = ranking_df.pivot(
            index="Variable", 
            columns=["Muestra 1", "Muestra 2"], 
            values="Importancia Permutación RF (%)"
        )
    else:
        pivot_matrix_df = pd.DataFrame()

    return pd.DataFrame(summary_records), pivot_matrix_df


def add_multivariate_tab_to_excel(excel_path, summary, ranking_pivot, sheet_name="Análisis Multivariado Global"):
    """
    Appends the 'Análisis Multivariado Global' sheet containing the Random Forest summary 
    and the pivoted Feature Importance Matrix.
    """
    workbook = openpyxl.load_workbook(excel_path)
    if sheet_name in workbook.sheetnames:
        workbook.remove(workbook[sheet_name])
    worksheet = workbook.create_sheet(title=sheet_name)

    # Excel styling parameters
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    section_font = Font(name="Calibri", size=11, bold=True, color="1F4E79")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=10, bold=True)
    regular_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # Title & Subtitle
    worksheet.cell(row=1, column=1, value="ANÁLISIS ESTADÍSTICO MULTIVARIADO (p VARIABLES)").font = title_font
    worksheet.cell(
        row=2,
        column=1,
        value="Filtros aplicados: is_edge = False e is_over_50um = True | Importancia calculada por Permutación (roc_auc)",
    ).font = Font(italic=True, size=10, color="595959")

    # 1. Global Random Forest Summary Table
    worksheet.cell(row=4, column=1, value="1. Resumen de Clasificación Multivariada Global (Random Forest)").font = section_font
    summary_df = summary if isinstance(summary, pd.DataFrame) else pd.DataFrame([summary])
    for row_index, row in enumerate(
        dataframe_to_rows(summary_df, index=False, header=True), start=5
    ):
        worksheet.append(row)
        for cell in worksheet[worksheet.max_row]:
            cell.border = thin_border
            if row_index == 5:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            else:
                cell.font = regular_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if isinstance(cell.value, float):
                    cell.value = round(cell.value, 4)

    # 2. Feature Importance Matrix (Pivoted Table)
    ranking_start = worksheet.max_row + 3
    worksheet.cell(
        row=ranking_start, column=1,
        value="2. Matriz de Contribución por Variable - Importancia Permutación RF (%)",
    ).font = section_font

    header_row_1 = ranking_start + 1
    header_row_2 = ranking_start + 2

    # Top-left cell header
    c_var1 = worksheet.cell(row=header_row_1, column=1, value="Variable")
    c_var1.fill = header_fill
    c_var1.font = header_font
    c_var1.alignment = Alignment(horizontal="center", vertical="center")
    c_var1.border = thin_border

    c_var2 = worksheet.cell(row=header_row_2, column=1, value="")
    c_var2.fill = header_fill
    c_var2.font = header_font
    c_var2.border = thin_border

    # Write column headers (Sample Pairs)
    pairs = ranking_pivot.columns
    for col_idx, (m1, m2) in enumerate(pairs, start=2):
        cell_m1 = worksheet.cell(row=header_row_1, column=col_idx, value=str(m1))
        cell_m1.fill = header_fill
        cell_m1.font = header_font
        cell_m1.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell_m1.border = thin_border

        cell_m2 = worksheet.cell(row=header_row_2, column=col_idx, value=str(m2))
        cell_m2.fill = header_fill
        cell_m2.font = header_font
        cell_m2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell_m2.border = thin_border

    # Write feature rows and importance values
    for row_idx, (var_name, row_series) in enumerate(ranking_pivot.iterrows(), start=header_row_2 + 1):
        c_var = worksheet.cell(row=row_idx, column=1, value=str(var_name))
        c_var.font = bold_font
        c_var.alignment = Alignment(horizontal="left", vertical="center")
        c_var.border = thin_border

        for col_idx, val in enumerate(row_series, start=2):
            c_val = worksheet.cell(row=row_idx, column=col_idx, value=float(val) if pd.notnull(val) else None)
            c_val.font = regular_font
            c_val.alignment = Alignment(horizontal="right", vertical="center")
            c_val.border = thin_border
            if c_val.value is not None:
                c_val.number_format = "0.0000"

    # Auto-adjust column widths
    for column in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        column_letter = openpyxl.utils.get_column_letter(column[0].column)
        worksheet.column_dimensions[column_letter].width = max(max_length + 3, 14)

    workbook.save(excel_path)


# ==========================================
# 3. BIVARIATE (2D) KOLMOGOROV-SMIRNOV TEST
# ==========================================
def ks2d2s(x1, y1, x2, y2):
    """
    Computes two-sample 2D Kolmogorov-Smirnov test statistic (D) and approximate p-value.
    """
    x1, y1 = np.asarray(x1, dtype=float), np.asarray(y1, dtype=float)
    x2, y2 = np.asarray(x2, dtype=float), np.asarray(y2, dtype=float)
    n1, n2 = len(x1), len(x2)
    if n1 == 0 or n2 == 0:
        return np.nan, np.nan

    d1 = np.column_stack([x1, y1])
    d2 = np.column_stack([x2, y2])
    all_x = np.concatenate([x1, x2])
    all_y = np.concatenate([y1, y2])

    eval_x, eval_y = all_x, all_y
    if len(eval_x) > 400:
        idx = np.random.choice(len(eval_x), 400, replace=False)
        eval_x, eval_y = eval_x[idx], eval_y[idx]

    f1_q1 = np.mean((d1[:, 0][:, None] <= eval_x[None, :]) & (d1[:, 1][:, None] <= eval_y[None, :]), axis=0)
    f2_q1 = np.mean((d2[:, 0][:, None] <= eval_x[None, :]) & (d2[:, 1][:, None] <= eval_y[None, :]), axis=0)
    f1_q2 = np.mean((d1[:, 0][:, None] <= eval_x[None, :]) & (d1[:, 1][:, None] >= eval_y[None, :]), axis=0)
    f2_q2 = np.mean((d2[:, 0][:, None] <= eval_x[None, :]) & (d2[:, 1][:, None] >= eval_y[None, :]), axis=0)
    f1_q3 = np.mean((d1[:, 0][:, None] >= eval_x[None, :]) & (d1[:, 1][:, None] <= eval_y[None, :]), axis=0)
    f2_q3 = np.mean((d2[:, 0][:, None] >= eval_x[None, :]) & (d2[:, 1][:, None] <= eval_y[None, :]), axis=0)
    f1_q4 = np.mean((d1[:, 0][:, None] >= eval_x[None, :]) & (d1[:, 1][:, None] >= eval_y[None, :]), axis=0)
    f2_q4 = np.mean((d2[:, 0][:, None] >= eval_x[None, :]) & (d2[:, 1][:, None] >= eval_y[None, :]), axis=0)

    d_max = max(
        np.max(np.abs(f1_q1 - f2_q1)),
        np.max(np.abs(f1_q2 - f2_q2)),
        np.max(np.abs(f1_q3 - f2_q3)),
        np.max(np.abs(f1_q4 - f2_q4))
    )

    n_eff = (n1 * n2) / (n1 + n2)
    r1 = np.corrcoef(x1, y1)[0, 1] if n1 > 1 else 0
    r2 = np.corrcoef(x2, y2)[0, 1] if n2 > 1 else 0
    r = np.nanmean([r1, r2])
    if np.isnan(r):
        r = 0.0

    denom = 1.0 + np.sqrt(1.0 - r**2) * (0.25 - 0.75 / np.sqrt(n_eff))
    z = d_max * np.sqrt(n_eff) / denom if denom > 0 else d_max * np.sqrt(n_eff)
    p_val = 2.0 * np.exp(-2.0 * (z ** 2))
    p_val = np.clip(p_val, 0.0, 1.0)
    return d_max, p_val


# ==========================================
# 4. MAIN PROCESSING PIPELINE AND EXPORT
# ==========================================
def process_all_mosaics(root_directory, output_excel="Resultados_Poros_Global.xlsx"):
    root_directory = os.path.abspath(os.path.expanduser(root_directory))
    if not os.path.exists(root_directory):
        print(f"❌ ERROR: Specified path does not exist: '{root_directory}'")
        return

    print(f"Searching for .h5 / .hdf5 files in: {root_directory}\n")
    h5_files = []
    for dirpath, _, filenames in os.walk(root_directory):
        for filename in filenames:
            if filename.lower().endswith((".h5", ".hdf5")):
                h5_files.append(os.path.join(dirpath, filename))

    if not h5_files:
        print("⚠️ No .h5 or .hdf5 files found in directory.")
        return

    print(f"✅ Found {len(h5_files)} data files. Processing...")
    file_dfs = {}
    for file_path in h5_files:
        filename_only = os.path.basename(file_path)
        df = process_h5_file(file_path)
        if df is not None and not df.empty:
            file_dfs[filename_only] = df
            print(f"  ✓ {filename_only}: {len(df)} interior pores processed.")
        else:
            print(f"  ✗ {filename_only}: No processable data.")

    if not file_dfs:
        print("\nNo valid pore data could be extracted from any file.")
        return

    # A. Perform Pairwise 2D Kolmogorov-Smirnov Tests (Irregularity [rad] vs. Elongation)
    ks_rows = []
    filenames_list = list(file_dfs.keys())
    for i in range(len(filenames_list)):
        for j in range(i + 1, len(filenames_list)):
            f1, f2 = filenames_list[i], filenames_list[j]
            d1 = file_dfs[f1][["irregularity_rad", "pore_elongation"]].dropna()
            d2 = file_dfs[f2][["irregularity_rad", "pore_elongation"]].dropna()

            d_stat, p_val_ks = ks2d2s(
                d1["irregularity_rad"], d1["pore_elongation"],
                d2["irregularity_rad"], d2["pore_elongation"]
            )
            p_ks_str = f"{p_val_ks:.2e}" if (not np.isnan(p_val_ks) and p_val_ks < 0.001) else (round(p_val_ks, 4) if not np.isnan(p_val_ks) else "N/A")
            ks_rows.append({
                "Muestra 1": f1.replace(".h5", "").replace(".hdf5", ""),
                "Muestra 2": f2.replace(".h5", "").replace(".hdf5", ""),
                "Estadístico D (K-S 2D)": round(d_stat, 4) if not np.isnan(d_stat) else "N/A",
                "p-valor (K-S 2D)": p_ks_str,
                "Sig. K-S 2D (α=0.05)": "Sí" if (not np.isnan(p_val_ks) and p_val_ks < 0.05) else "No"
            })
    df_ks = pd.DataFrame(ks_rows)

    # B. Generate 2D Kernel Density Estimation (KDE) Plot Mosaic
    img_kde_path = os.path.join(root_directory, "temp_kde.png")
    num_samples = len(file_dfs)
    cols = 2 if num_samples > 1 else 1
    rows = math.ceil(num_samples / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 5 * rows), sharex=True, sharey=True)
    if num_samples == 1:
        axes = np.array([axes])
    axes_flat = axes.flatten()

    for idx, (filename, df) in enumerate(file_dfs.items()):
        ax = axes_flat[idx]
        clean_name = filename.replace(".h5", "").replace(".hdf5", "")
        df_clean = df[["irregularity_rad", "pore_elongation"]].dropna()

        sns.kdeplot(
            data=df_clean, x="irregularity_rad", y="pore_elongation",
            ax=ax, cmap="Blues", fill=True, thresh=0.05, levels=10
        )
        ax.scatter(df_clean["irregularity_rad"], df_clean["pore_elongation"], s=6, alpha=0.15, color='darkblue')
        ax.set_title(f"Muestra: {clean_name} (n={len(df_clean)})", fontsize=11, fontweight='bold')
        ax.set_xlabel("Irregularidad (rad)", fontsize=10)
        ax.set_ylabel("Elongación (pore_elongation)", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.4)

    for idx in range(num_samples, len(axes_flat)):
        axes_flat[idx].axis('off')

    plt.suptitle("Mapas de Densidad Kernel 2D (Irregularidad [rad] vs. Elongación)", fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout()
    plt.savefig(img_kde_path, dpi=200, bbox_inches='tight')
    plt.close()

    # C. Export Results to Excel
    excel_path = os.path.join(root_directory, output_excel)
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_ks.to_excel(writer, sheet_name="Prueba K-S 2D", index=False)

    # D. Format "Prueba K-S 2D" Sheet and Insert Scaled 2D KDE Plot (1/4 area)
    wb = openpyxl.load_workbook(excel_path)
    ws_ks = wb["Prueba K-S 2D"]

    # Formatting table headers
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"), right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"), bottom=Side(style="thin", color="D9D9D9")
    )
    for cell in ws_ks[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    # Adjust table cell borders and alignment
    for row in ws_ks.iter_rows(min_row=2, max_row=ws_ks.max_row, min_col=1, max_col=ws_ks.max_column):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Add 2D KDE Plot Image scaled to 1/4 size (half width and half height)
    image_row = ws_ks.max_row + 3
    ws_ks.cell(row=image_row - 1, column=1, value="Gráficos de Densidad Kernel 2D (Irregularidad [rad] vs. Elongación)").font = Font(name="Calibri", size=12, bold=True, color="1F4E79")
    img_kde = Image(img_kde_path)
    img_kde.width = int(img_kde.width / 2)
    img_kde.height = int(img_kde.height / 2)
    ws_ks.add_image(img_kde, f"A{image_row}")

    # Auto-fit column widths
    for column in ws_ks.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        col_letter = openpyxl.utils.get_column_letter(column[0].column)
        ws_ks.column_dimensions[col_letter].width = max(max_length + 3, 16)

    wb.save(excel_path)

    # E. Run Global Multivariate Analysis (if at least 2 samples exist)
    if len(file_dfs) >= 2:
        multivariate_df = pd.concat(
            [
                df.assign(Muestra=os.path.splitext(filename)[0])
                for filename, df in file_dfs.items()
            ],
            ignore_index=True,
        )
        try:
            summary_mv, ranking_pivot_mv = run_multivariate_analysis(multivariate_df)
            add_multivariate_tab_to_excel(excel_path, summary_mv, ranking_pivot_mv)
        except ValueError as error:
            print(f"Could not perform multivariate analysis: {error}")

    # Clean up temporary image files
    if os.path.exists(img_kde_path):
        os.remove(img_kde_path)

    print(f"\nProcessing completed successfully!")
    print(f"📊 Excel file saved at: {excel_path}")


# ==========================================
# SCRIPT EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    CARPETA_RAIZ = r"H:\Otros ordenadores\Microscopio\Silvia EEUU\Porosidad de los mosaicos 4"
    process_all_mosaics(CARPETA_RAIZ)