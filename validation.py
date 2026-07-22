import pandas as pd


def build_registered_name_set(registered_df):
    """
    Build a set of normalized full names from registered_df.

    Supports:
      - A 'Full Name' column, OR
      - First and last name in the first two columns (no header).
    """
    if "Full Name" in registered_df.columns:
        names = registered_df["Full Name"].astype(str)
    else:
        if registered_df.shape[1] < 2:
            raise ValueError("registered.csv must have at least two columns for first and last name.")

        first = registered_df.iloc[:, 0].astype(str)
        last = registered_df.iloc[:, 1].astype(str)
        names = first.str.cat(last, sep=" ")

    # Normalize
    names = (
        names.str.replace("\xa0", " ", regex=False)
             .str.strip()
             .str.lower()
    )
    return set(names.tolist())


def build_roommate_validation(students_df, registered_df):
    """
    Return only the rows where InRegistered == False.
    Columns:
      - Student
      - Request Number
      - Requested Name
      - InRegistered
    """
    registered_names = build_registered_name_set(registered_df)
    rows = []

    for _, row in students_df.iterrows():
        student_name = str(row["Full Name"]).replace("\xa0", " ").strip()

        for i in range(1, 4):
            col = f"Request {i}"
            if col not in students_df.columns:
                continue

            val = row.get(col)
            if pd.isna(val):
                continue

            requested_name = str(val).replace("\xa0", " ").strip()
            if not requested_name:
                continue

            in_reg = requested_name.lower() in registered_names

            # Only include *invalid* requests
            if not in_reg:
                rows.append({
                    "Student": student_name,
                    "Request Number": i,
                    "Requested Name": requested_name,
                    "InRegistered": False
                })

    return pd.DataFrame(rows)


def main():
    students_path = "students.csv"
    registered_path = "registered.csv"
    output_path = "roommate_selection_validation.csv"

    students_df = pd.read_csv(students_path)

    # Your example registered.csv has no header row → use header=None
    registered_df = pd.read_csv(registered_path, header=None)

    invalid_df = build_roommate_validation(students_df, registered_df)

    if invalid_df.empty:
        print("All roommate requests are valid!")
    else:
        print("Invalid roommate requests:\n")
        print(invalid_df.to_string(index=False))

    invalid_df.to_csv(output_path, index=False)
    print(f"\nInvalid requests written to {output_path}")


if __name__ == "__main__":
    main()
