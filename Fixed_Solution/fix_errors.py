import pandas as pd
import sys

ERRORS_FILE = "errors_raw.csv"
STUDENTS_FILE = "students.csv"

errors = pd.read_csv(ERRORS_FILE)
df = pd.read_csv(STUDENTS_FILE)

if errors.empty:
    print("No errors detected — nothing to fix.")
    sys.exit(0)

fixes_applied = []

registered_df = pd.read_csv("registered.csv", header=None)
reg_first = registered_df.iloc[:, 0].astype(str).str.replace("\xa0", " ", regex=False).str.strip()
reg_last = registered_df.iloc[:, 1].astype(str).str.replace("\xa0", " ", regex=False).str.strip()
reg_full = reg_first + " " + reg_last
registered_names = set(reg_full.str.lower())
reg_lookup = {}
for i in range(len(registered_df)):
    fn = reg_full.iloc[i].strip()
    grade = str(registered_df.iloc[i, 3]).strip() if registered_df.shape[1] > 3 else ""
    first_val = reg_first.iloc[i]
    last_val = reg_last.iloc[i]
    if first_val == first_val.upper() or first_val == first_val.lower():
        first_val = first_val.title()
    if last_val == last_val.upper() or last_val == last_val.lower():
        last_val = last_val.title()
    reg_lookup[fn.lower()] = {
        "first": first_val,
        "last": last_val,
        "full": fn,
        "grade": grade
    }

gender_errors = errors[errors["Error Type"] == "Invalid Gender"]
for _, err in gender_errors.iterrows():
    fix = str(err["Suggested Fix"]).strip()
    if fix and fix != "nan":
        mask = df["Full Name"] == err["Student"]
        df.loc[mask, "Gender"] = fix
        fixes_applied.append(f"Gender: '{err['Student']}' → '{fix}'")

missing_last = errors[errors["Error Type"] == "Missing Last Name"]
for _, err in missing_last.iterrows():
    fix = str(err["Suggested Fix"]).strip()
    if fix and fix != "nan":
        mask = df["Full Name"] == err["Student"]
        df.loc[mask, "Legal Last Name"] = fix
        fixes_applied.append(f"Missing Last Name: '{err['Student']}' → '{fix}'")

count_errors = errors[errors["Error Type"] == "Invalid Roommate Count"]
col_num = "Number of Requested Roommates (including yourself):"
for _, err in count_errors.iterrows():
    fix = str(err["Suggested Fix"]).strip()
    if fix and fix != "nan":
        mask = df["Full Name"] == err["Student"]
        df.loc[mask, col_num] = int(fix)
        fixes_applied.append(f"Roommate Count: '{err['Student']}' → {fix}")

name_renames = {}

mismatch_errors = errors[errors["Error Type"] == "Name Mismatch"]
for _, err in mismatch_errors.iterrows():
    student = str(err["Student"]).strip()
    legal_name = str(err["Suggested Fix"]).strip()
    if not legal_name or legal_name == "nan":
        continue
    if student.lower() in registered_names:
        row_mask = df["Full Name"] == student
        if row_mask.any():
            parts = student.split(" ", 1)
            if len(parts) == 2:
                df.loc[row_mask, "Legal First Name"] = parts[0]
                df.loc[row_mask, "Legal Last Name"] = parts[1]
                fixes_applied.append(f"Legal Name Fix: '{student}' legal → '{student}'")
    elif legal_name.lower() in registered_names:
        name_renames[student] = legal_name
        fixes_applied.append(f"Full Name: '{student}' → '{legal_name}'")

reg_errors = errors[errors["Error Type"] == "Name Not Registered"]
for _, err in reg_errors.iterrows():
    fix = str(err["Suggested Fix"]).strip()
    old = str(err["Student"]).strip()
    if fix and fix != "nan" and fix.lower() != old.lower():
        if fix.lower() not in registered_names:
            continue
        if old in name_renames:
            continue
        name_renames[old] = fix

request_cols = ["Request 1", "Request 2", "Request 3"]

for old, new in name_renames.items():
    mask = df["Full Name"] == old
    if mask.any():
        df.loc[mask, "Full Name"] = new
        reg_info = reg_lookup.get(new.lower())
        if reg_info:
            df.loc[mask, "Legal First Name"] = reg_info["first"]
            df.loc[mask, "Legal Last Name"] = reg_info["last"]
            if reg_info["grade"]:
                df.loc[mask, "Grade:"] = int(reg_info["grade"])
    for col in request_cols:
        df[col] = df[col].replace(old, new)
    fixes_applied.append(f"Full Name: '{old}' → '{new}' (all fields updated)")

notfound = errors[errors["Error Type"] == "Name Not Found"]
for _, err in notfound.iterrows():
    fix = str(err["Suggested Fix"]).strip()
    detail = str(err["Details"])
    bad_name = detail.split("'")[1] if "'" in detail else ""
    if fix and fix != "nan" and bad_name:
        fix = name_renames.get(fix, fix)
        for col in request_cols:
            df[col] = df[col].replace(bad_name, fix)
        fixes_applied.append(f"Request Name: '{bad_name}' → '{fix}'")

fixes_applied = list(dict.fromkeys(fixes_applied))

dup_errors = errors[errors["Error Type"] == "Duplicate Request"]
for _, err in dup_errors.iterrows():
    student = str(err["Student"]).strip()
    student = name_renames.get(student, student)
    req_num = int(err["Request Number"])
    col = f"Request {req_num}"

    mask = df["Full Name"] == student
    if not mask.any():
        continue

    idx = df.index[mask][0]
    current_requests = set()
    for rc in request_cols:
        v = df.loc[idx, rc]
        if pd.notna(v) and str(v).strip():
            current_requests.add(str(v).strip())

    candidates = []
    for _, other in df.iterrows():
        if other["Full Name"] == student:
            continue
        for rc in request_cols:
            v = other.get(rc)
            if pd.notna(v) and str(v).strip() == student:
                if other["Full Name"] not in current_requests:
                    candidates.append(other["Full Name"])
                break

    if candidates:
        replacement = candidates[0]
        df.loc[idx, col] = replacement
        grade_col = f"Roommate {req_num}'s Grade:"
        rep_mask = df["Full Name"] == replacement
        if rep_mask.any():
            df.loc[idx, grade_col] = df.loc[rep_mask, "Grade:"].iloc[0]
        fixes_applied.append(f"Duplicate Fix: '{student}' Request {req_num} → '{replacement}'")

grade_errors = errors[errors["Error Type"] == "Grade Mismatch"]
for _, err in grade_errors.iterrows():
    student = name_renames.get(str(err["Student"]).strip(), str(err["Student"]).strip())
    req_num = int(err["Request Number"])
    fix = str(err["Suggested Fix"]).strip()
    if fix and fix != "nan":
        grade_col = f"Roommate {req_num}'s Grade:"
        mask = df["Full Name"] == student
        df.loc[mask, grade_col] = int(fix)
        fixes_applied.append(f"Grade Fix: '{student}' Request {req_num} grade → {fix}")

OUTPUT_FILE = "students_corrected.csv"
df.to_csv(OUTPUT_FILE, index=False)

print(f"Applied {len(fixes_applied)} fixes from {ERRORS_FILE}:\n")
for f in fixes_applied:
    print(f"  - {f}")
print(f"\nPatched file saved to {OUTPUT_FILE}")
print(f"Original {STUDENTS_FILE} is unchanged.")
