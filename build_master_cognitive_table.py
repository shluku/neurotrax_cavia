from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
import zipfile


SPECIAL_CODES = {"FP", "DI", "NA", "N/A"}
NS_MAIN = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def excel_col_to_idx(col: str) -> int:
    v = 0
    for ch in col:
        if not ch.isalpha():
            break
        v = v * 26 + (ord(ch.upper()) - ord("A") + 1)
    return max(0, v - 1)


def parse_cell_ref(ref: str) -> Tuple[int, int]:
    letters = "".join(ch for ch in ref if ch.isalpha())
    digits = "".join(ch for ch in ref if ch.isdigit())
    col = excel_col_to_idx(letters) if letters else 0
    row = int(digits) - 1 if digits else 0
    return row, col


def _xlsx_read_all_sheets(path: Path) -> Dict[str, pd.DataFrame]:
    with zipfile.ZipFile(path, "r") as zf:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(".//x:si", NS_MAIN):
                texts = [t.text or "" for t in si.findall(".//x:t", NS_MAIN)]
                shared.append("".join(texts))

        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rels_map: Dict[str, str] = {}
        for rel in rels_root.findall(".//{*}Relationship"):
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if rid:
                if not target.startswith("xl/"):
                    target = f"xl/{target}"
                rels_map[rid] = target

        wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = wb_root.findall(".//x:sheet", NS_MAIN)
        out: Dict[str, pd.DataFrame] = {}

        for sh in sheets:
            name = sh.attrib.get("name", "Sheet")
            rid = sh.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            if not rid or rid not in rels_map:
                continue
            sheet_path = rels_map[rid]
            if sheet_path not in zf.namelist():
                continue
            root = ET.fromstring(zf.read(sheet_path))
            sheet_data = root.find(".//x:sheetData", NS_MAIN)
            if sheet_data is None:
                out[name] = pd.DataFrame()
                continue

            grid: Dict[Tuple[int, int], object] = {}
            max_row = -1
            max_col = -1
            for row_el in sheet_data.findall("x:row", NS_MAIN):
                for c in row_el.findall("x:c", NS_MAIN):
                    ref = c.attrib.get("r", "")
                    r_idx, c_idx = parse_cell_ref(ref)
                    max_row = max(max_row, r_idx)
                    max_col = max(max_col, c_idx)
                    t = c.attrib.get("t")
                    v_el = c.find("x:v", NS_MAIN)
                    is_el = c.find("x:is", NS_MAIN)

                    val: object = None
                    if t == "s" and v_el is not None and v_el.text is not None:
                        try:
                            si = int(v_el.text)
                            val = shared[si] if 0 <= si < len(shared) else v_el.text
                        except Exception:
                            val = v_el.text
                    elif t == "inlineStr" and is_el is not None:
                        texts = [t2.text or "" for t2 in is_el.findall(".//x:t", NS_MAIN)]
                        val = "".join(texts)
                    elif v_el is not None and v_el.text is not None:
                        val = v_el.text
                    grid[(r_idx, c_idx)] = val

            if max_row < 0 or max_col < 0:
                out[name] = pd.DataFrame()
                continue

            matrix = [[None] * (max_col + 1) for _ in range(max_row + 1)]
            for (r, c), v in grid.items():
                matrix[r][c] = v
            raw = pd.DataFrame(matrix)
            if raw.shape[0] >= 1:
                hdr = raw.iloc[0].fillna("")
                cols = []
                for i, h in enumerate(hdr):
                    hs = str(h).strip()
                    cols.append(hs if hs else f"col_{i+1}")
                df = raw.iloc[1:].copy()
                df.columns = cols
                df = df.reset_index(drop=True)
            else:
                df = raw
            out[name] = df
        return out


def normalize_key(v: object) -> Optional[str]:
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s if s else None


def first_existing_col(columns: List[str], candidates: List[str]) -> Optional[str]:
    norm_map = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        key = cand.lower().strip()
        if key in norm_map:
            return norm_map[key]
    return None


def find_sheet_by_keywords(sheet_names: List[str], keywords: List[str]) -> Optional[str]:
    hits = []
    for s in sheet_names:
        sl = s.lower()
        if all(k in sl for k in keywords):
            hits.append(s)
    if not hits:
        return None
    hits.sort(key=len)
    return hits[0]


def find_subjects_sheet(sheet_names: List[str]) -> Optional[str]:
    for s in sheet_names:
        if s.lower().strip() in {"subjects", "subject"}:
            return s
    for s in sheet_names:
        if "subject" in s.lower():
            return s
    return sheet_names[0] if sheet_names else None


def summarize_sheet(df: pd.DataFrame) -> Dict[str, object]:
    non_empty_rows = int(df.notna().any(axis=1).sum())
    return {
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "columns": list(df.columns),
        "non_empty_rows": non_empty_rows,
    }


def is_meaningful_value(v: object) -> bool:
    if pd.isna(v):
        return False
    txt = str(v).strip()
    return txt != ""


def drop_artifact_columns(df: pd.DataFrame, keep_cols: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    drop_cols: List[str] = []
    out = df.copy()
    for c in list(out.columns):
        if c in keep_cols:
            continue
        cl = c.lower().strip()
        if cl.startswith("col_"):
            ser = out[c]
            meaningful = ser.apply(is_meaningful_value).sum()
            if int(meaningful) == 0:
                drop_cols.append(c)
    if drop_cols:
        out = out.drop(columns=drop_cols, errors="ignore")
    return out, drop_cols


def is_missing_like(v: object) -> bool:
    if pd.isna(v):
        return True
    return str(v).strip() == ""


def cognitive_non_missing_count(df: pd.DataFrame, cognitive_cols: List[str]) -> pd.Series:
    if not cognitive_cols:
        return pd.Series([0] * len(df), index=df.index)
    miss = df[cognitive_cols].isna() | (df[cognitive_cols].astype(str).apply(lambda col: col.str.strip()) == "")
    return (~miss).sum(axis=1)


def clean_and_prepare_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    prefix: str,
    id_n_col: str,
    id_d_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, List[Dict[str, object]], List[Dict[str, object]]]:
    flags: List[Dict[str, object]] = []
    dictionary_rows: List[Dict[str, object]] = []

    out = df.copy()
    out[id_n_col] = out[id_n_col].apply(normalize_key)
    if id_d_col and id_d_col in out.columns:
        out[id_d_col] = out[id_d_col].astype("string")

    keep_cols = [id_n_col] + ([id_d_col] if id_d_col and id_d_col in out.columns else [])
    out, dropped_artifacts = drop_artifact_columns(out, keep_cols)
    if dropped_artifacts:
        print(f"Dropped artifact columns from {sheet_name}: {dropped_artifacts}")
    value_cols = [c for c in out.columns if c not in keep_cols]

    renamed = {}
    for col in value_cols:
        new_col = f"{prefix}{col.strip()}"
        renamed[col] = new_col

    for source_col in value_cols:
        master_col = renamed[source_col]
        series = out[source_col]

        special_seen = set()
        converted_vals = []
        non_missing = 0
        numeric_convertible = 0

        for idx, raw in series.items():
            if pd.isna(raw):
                converted_vals.append(np.nan)
                continue

            sval = str(raw).strip()
            if not sval:
                converted_vals.append(np.nan)
                continue

            non_missing += 1
            code = sval.upper()
            if code in SPECIAL_CODES:
                special_seen.add(code)
                flags.append(
                    {
                        "source_sheet": sheet_name,
                        "source_column": source_col,
                        "master_column": master_col,
                        "row_index": int(idx),
                        "Subject_ID_N": out.at[idx, id_n_col],
                        "Subject_ID_D": out.at[idx, id_d_col] if id_d_col and id_d_col in out.columns else "",
                        "raw_value": sval,
                    }
                )
                converted_vals.append(np.nan)
                continue

            num = pd.to_numeric(pd.Series([sval]), errors="coerce").iloc[0]
            if pd.notna(num):
                numeric_convertible += 1
                converted_vals.append(float(num))
            else:
                converted_vals.append(np.nan)

        out[master_col] = converted_vals
        dictionary_rows.append(
            {
                "source_sheet": sheet_name,
                "source_column": source_col,
                "master_column": master_col,
                "number_of_non_missing_values": non_missing,
                "number_of_numeric_convertible_values": numeric_convertible,
                "special_codes_seen": "|".join(sorted(special_seen)),
            }
        )

    out = out[[id_n_col] + ([id_d_col] if id_d_col and id_d_col in out.columns else []) + list(renamed.values())]
    out = out.drop_duplicates(subset=[id_n_col], keep="first")
    return out, flags, dictionary_rows


def build_delta_consistency_report(master: pd.DataFrame) -> pd.DataFrame:
    cols = list(master.columns)
    lower_map = {c.lower(): c for c in cols}

    triples = []
    for c in cols:
        cl = c.lower()
        if "_t1" in cl:
            base = cl.replace("_t1", "")
            c_t2 = lower_map.get(f"{base}_t2")
            c_delta = lower_map.get(f"{base}_delta")
            if c_t2 and c_delta:
                triples.append((c, c_t2, c_delta, base))

    rows: List[Dict[str, object]] = []
    sid_col = "Subject_ID_N" if "Subject_ID_N" in master.columns else master.columns[0]

    for c_t1, c_t2, c_delta, base in triples:
        t1 = pd.to_numeric(master[c_t1], errors="coerce")
        t2 = pd.to_numeric(master[c_t2], errors="coerce")
        d = pd.to_numeric(master[c_delta], errors="coerce")
        calc = t2 - t1
        diff = (d - calc).abs()

        mask = t1.notna() & t2.notna() & d.notna() & (diff > 0.11)
        bad = master[mask]
        for i in bad.index:
            rows.append(
                {
                    "Subject_ID_N": master.at[i, sid_col],
                    "t1_column": c_t1,
                    "t2_column": c_t2,
                    "delta_column": c_delta,
                    "reported_delta": d.at[i],
                    "computed_delta_t2_minus_t1": calc.at[i],
                    "abs_difference": diff.at[i],
                    "metric_base": base,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build clean master cognitive table from Limor NeuroTrax workbook.")
    parser.add_argument("--input", type=Path, default=Path("עותק של DATA_04.26_LIMOR.xlsx"))
    parser.add_argument("--out-dir", type=Path, default=Path("output/cognitive_master"))
    args = parser.parse_args()

    input_path = args.input
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    print(f"Workbook: {input_path}")
    try:
        xls = pd.ExcelFile(input_path)
        sheet_names = list(xls.sheet_names)
        all_sheets = {s: pd.read_excel(input_path, sheet_name=s, dtype=object) for s in sheet_names}
    except Exception as e:
        print(f"Excel engine fallback engaged ({e}). Reading via zip/xml parser.")
        all_sheets = _xlsx_read_all_sheets(input_path)
        sheet_names = list(all_sheets.keys())

    print(f"Sheets found: {len(sheet_names)}")
    for s in sheet_names:
        sm = summarize_sheet(all_sheets[s])
        print(f"\n[{s}]")
        print(f"rows={sm['rows']} cols={sm['cols']} non_empty_rows={sm['non_empty_rows']}")
        print(f"columns={sm['columns']}")

    subjects_sheet = find_subjects_sheet(sheet_names)
    if not subjects_sheet:
        raise RuntimeError("Could not locate subjects sheet.")

    sheet_map = {
        "overall_": find_sheet_by_keywords(sheet_names, ["overall"]),
        "mem_": find_sheet_by_keywords(sheet_names, ["mem"]),
        "ef_": find_sheet_by_keywords(sheet_names, ["ef"]),
        "attn_": find_sheet_by_keywords(sheet_names, ["att"]),
        "ps_": find_sheet_by_keywords(sheet_names, ["processing"]),
        "verbal_": find_sheet_by_keywords(sheet_names, ["verbal"]),
        "motor_": find_sheet_by_keywords(sheet_names, ["motor"]),
    }

    print("\nSelected sheets:")
    print(f"subjects -> {subjects_sheet}")
    for p, s in sheet_map.items():
        print(f"{p} -> {s}")

    subjects = all_sheets[subjects_sheet].copy()
    id_n_col = first_existing_col(list(subjects.columns), ["Subject_ID_N", "subject_id_n", "Subject ID N"])
    id_d_col = first_existing_col(list(subjects.columns), ["Subject_ID_D", "subject_id_d", "Subject ID D"])
    if not id_n_col:
        raise RuntimeError("Subject_ID_N column not found in subjects sheet.")

    subjects[id_n_col] = subjects[id_n_col].apply(normalize_key)
    if id_d_col:
        subjects[id_d_col] = subjects[id_d_col].astype("string")

    master = subjects.copy()
    if id_n_col != "Subject_ID_N":
        master = master.rename(columns={id_n_col: "Subject_ID_N"})
        id_n_col = "Subject_ID_N"
    if id_d_col and id_d_col != "Subject_ID_D":
        master = master.rename(columns={id_d_col: "Subject_ID_D"})
        id_d_col = "Subject_ID_D"

    all_flags: List[Dict[str, object]] = []
    data_dict_rows: List[Dict[str, object]] = []

    for prefix, sheet_name in sheet_map.items():
        if not sheet_name:
            continue
        src = all_sheets[sheet_name].copy()

        local_id_n = first_existing_col(
            list(src.columns),
            [id_n_col, "Subject_ID_N", "subject_id_n", "Subject ID", "subject id"],
        )
        local_id_d = first_existing_col(list(src.columns), [id_d_col or "", "Subject_ID_D", "subject_id_d"])
        if not local_id_n:
            print(f"Skipping sheet {sheet_name}: missing Subject_ID_N")
            continue

        prepared, flags, dd = clean_and_prepare_sheet(src, sheet_name, prefix, local_id_n, local_id_d)

        if local_id_n != "Subject_ID_N":
            prepared = prepared.rename(columns={local_id_n: "Subject_ID_N"})
        if local_id_d and local_id_d in prepared.columns and local_id_d != "Subject_ID_D":
            prepared = prepared.rename(columns={local_id_d: "Subject_ID_D"})

        drop_cols = [c for c in prepared.columns if c == "Subject_ID_D" and c in master.columns]
        prepared = prepared.drop(columns=drop_cols, errors="ignore")

        master = master.merge(prepared, on="Subject_ID_N", how="left")
        all_flags.extend(flags)
        data_dict_rows.extend(dd)

    if "Subject_ID_D" in master.columns:
        master["Subject_ID_D"] = master["Subject_ID_D"].astype("string")

    cognitive_cols = [c for c in master.columns if any(c.startswith(p) for p in ["overall_", "mem_", "ef_", "attn_", "ps_", "verbal_", "motor_"])]
    nn_cog = cognitive_non_missing_count(master, cognitive_cols)

    # Drop only fully empty artifact rows:
    # Subject_ID_N missing, Subject_ID_D missing, Initials missing, and 0 cognitive values.
    sid_n_missing = master["Subject_ID_N"].apply(is_missing_like) if "Subject_ID_N" in master.columns else pd.Series([True]*len(master))
    sid_d_missing = master["Subject_ID_D"].apply(is_missing_like) if "Subject_ID_D" in master.columns else pd.Series([True]*len(master))
    initials_missing = master["Initials"].apply(is_missing_like) if "Initials" in master.columns else pd.Series([True]*len(master))
    artifact_mask = sid_n_missing & sid_d_missing & initials_missing & (nn_cog == 0)
    dropped_artifacts = int(artifact_mask.sum())
    if dropped_artifacts > 0:
        print(f"Dropping fully-empty artifact rows: {dropped_artifacts}")
        master = master.loc[~artifact_mask].copy()
        nn_cog = nn_cog.loc[~artifact_mask]

    # Report subjects with missing Subject_ID_D but with cognitive data.
    sid_d_missing_or_dash = (master["Subject_ID_D"].isna() | (master["Subject_ID_D"].astype(str).str.strip().isin(["", "-"]))) if "Subject_ID_D" in master.columns else pd.Series([True]*len(master), index=master.index)
    missing_label_with_data_mask = sid_d_missing_or_dash & (nn_cog > 0)
    missing_label_report = master.loc[missing_label_with_data_mask, [c for c in ["Initials", "Subject_ID_N", "Subject_ID_D", "age", "T1 date", "T2 date", "Time lap"] if c in master.columns]].copy()
    missing_label_report.insert(0, "row_index", missing_label_report.index)
    missing_label_report["non_missing_cognitive_columns"] = nn_cog.loc[missing_label_with_data_mask].values

    flags_df = pd.DataFrame(all_flags)
    if not flags_df.empty and "raw_value" in flags_df.columns:
        flags_df["raw_value"] = flags_df["raw_value"].astype(str).str.strip().str.upper()
        flags_df = flags_df[flags_df["raw_value"].isin(SPECIAL_CODES)].copy()
    dd_df = pd.DataFrame(data_dict_rows)
    delta_df = build_delta_consistency_report(master)

    master_path = out_dir / "master_cognitive_wide.csv"
    flags_path = out_dir / "cognitive_code_flags_long.csv"
    dd_path = out_dir / "cognitive_data_dictionary.csv"
    delta_path = out_dir / "delta_consistency_report.csv"
    readme_path = out_dir / "README_cognitive_master.md"
    missing_label_path = out_dir / "subjects_missing_device_label_id.csv"

    master.to_csv(master_path, index=False)
    missing_label_report.to_csv(missing_label_path, index=False)
    flags_df.to_csv(flags_path, index=False)
    dd_df.to_csv(dd_path, index=False)
    delta_df.to_csv(delta_path, index=False)

    with readme_path.open("w", encoding="utf-8") as f:
        f.write("# Cognitive Master Output\n\n")
        f.write(f"- Input workbook: `{input_path}`\n")
        f.write(f"- Subjects sheet: `{subjects_sheet}`\n")
        f.write("- Merge key: `Subject_ID_N`\n")
        f.write("- Subject string label preserved: `Subject_ID_D`\n\n")
        f.write("## Files\n")
        f.write("- `master_cognitive_wide.csv`\n")
        f.write("- `cognitive_code_flags_long.csv`\n")
        f.write("- `cognitive_data_dictionary.csv`\n")
        f.write("- `delta_consistency_report.csv`\n")

    n_subjects = int(master["Subject_ID_N"].nunique()) if "Subject_ID_N" in master.columns else int(master.shape[0])
    n_rows_master = int(master.shape[0])
    n_cols = int(master.shape[1])
    n_flags = int(flags_df.shape[0])
    n_delta_bad = int(delta_df.shape[0])

    print("\nValidation summary:")
    print(f"subjects_unique_id_n={n_subjects}")
    print(f"master_rows={n_rows_master}")
    print(f"master_columns={n_cols}")
    print(f"special_code_flags={n_flags}")
    print(f"delta_mismatches={n_delta_bad}")

    key_cols = [c for c in ["Subject_ID_N", "Subject_ID_D"] if c in master.columns]
    print("\nFirst 5 key-id rows:")
    print(master[key_cols].head(5).to_string(index=False))

    print("\nGenerated files:")
    for p in [master_path, flags_path, dd_path, delta_path, readme_path, missing_label_path]:
        print(p)


if __name__ == "__main__":
    main()
