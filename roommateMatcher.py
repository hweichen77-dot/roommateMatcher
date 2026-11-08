import pandas as pd

def load_data(file_path):
    """Load the student data from a CSV file."""
    return pd.read_csv(file_path)

def grades_touch(grades):
    """
    Return True if the distinct grades form a contiguous sequence.
    e.g. [9,10], [10,11], [9,10,11] are OK; [9,11] is not.
    """
    g = sorted(set(int(x) for x in grades if pd.notna(x)))
    if not g:
        return True
    return g[-1] - g[0] + 1 == len(g)

def create_rooms(data):
    """
    Create rooms of four students, with:
      - Gender separated.
      - Pairing-of-pairs:
          1) Make 2-person pairs (using roommate requests when possible).
          2) Combine two pairs to make rooms of 4.
      - Grade constraint: all grades in a room must 'touch'
        (no grade gaps, e.g., no 9th+11th without 10th).
    """
    data = data.copy()
    data["Assigned"] = False  # Track assigned students
    # Normalize grade to an integer column we can use easily
    if "Grade:" not in data.columns:
        raise ValueError("Input CSV must contain a 'Grade:' column for student grade.")
    data["GradeInt"] = data["Grade:"].astype(int)

    # Quick lookup from full name to index
    name_to_idx = {row["Full Name"]: idx for idx, row in data.iterrows()}

    def get_requests(idx):
        """Return a cleaned list of roommate request names for a student index."""
        row = data.loc[idx]
        reqs = []
        for i in range(1, 4):
            col = f"Request {i}"
            if col in data.columns:
                val = row.get(col)
                if isinstance(val, str) and val.strip():
                    reqs.append(val.strip())
        return reqs

    def make_pairs(gender):
        """
        For a given gender, return a list of 'pairs':
          - Mostly 2-person lists [i, j]
          - Possibly 1-person lists [i] for leftovers
        Indices i, j are row indices in `data`.
        """
        idxs = list(data.index[data["Gender"] == gender])
        unpaired = set(idxs)
        pairs = []

        # Precompute each student's requests by index
        requests_by_student = {i: get_requests(i) for i in idxs}

        # 1) Mutual-request-based pairs
        for i in idxs:
            if i not in unpaired:
                continue
            for rname in requests_by_student[i]:
                j = name_to_idx.get(rname)
                if j is None or j not in unpaired:
                    continue
                if data.loc[j, "Gender"] != gender:
                    continue
                # Mutual request?
                if data.loc[i, "Full Name"] in requests_by_student.get(j, []):
                    pairs.append([i, j])
                    unpaired.remove(i)
                    unpaired.remove(j)
                    break  # move to next i

        # 2) One-sided request pairs (if still unpaired)
        for i in idxs:
            if i not in unpaired:
                continue
            for rname in requests_by_student[i]:
                j = name_to_idx.get(rname)
                if j is None or j not in unpaired:
                    continue
                if data.loc[j, "Gender"] != gender:
                    continue
                pairs.append([i, j])
                unpaired.remove(i)
                unpaired.remove(j)
                break  # move to next i

        # 3) Arbitrary pairs for remaining students, pairing close grades together
        remaining = sorted(list(unpaired), key=lambda idx: data.loc[idx, "GradeInt"])
        while len(remaining) >= 2:
            i = remaining.pop(0)
            # Choose partner with closest grade
            best_j = None
            best_diff = None
            for j in remaining:
                diff = abs(data.loc[i, "GradeInt"] - data.loc[j, "GradeInt"])
                if best_diff is None or diff < best_diff:
                    best_diff = diff
                    best_j = j
            remaining.remove(best_j)
            pairs.append([i, best_j])

        # 4) If there is an odd one out, make them a singleton "pair"
        for i in remaining:
            pairs.append([i])

        return pairs

    def combine_pairs_to_rooms(pairs):
        """
        Combine 2-person 'pairs' into 4-person rooms while enforcing the
        grade-touching rule. Remaining pairs/singletons are packed greedily.
        """
        rooms = []
        used = set()

        # First, try to build perfect 4-person rooms from 2+2 pairs
        for idx_p, p in enumerate(pairs):
            if idx_p in used or len(p) != 2:
                continue
            for idx_q, q in enumerate(pairs):
                if idx_q <= idx_p or idx_q in used or len(q) != 2:
                    continue
                combo = p + q  # four student indices
                grades = data.loc[combo, "GradeInt"].tolist()
                if grades_touch(grades):
                    used.add(idx_p)
                    used.add(idx_q)
                    for s in combo:
                        data.loc[s, "Assigned"] = True
                    rooms.append([data.loc[s, "Full Name"] for s in combo])
                    break  # move to next p

        # Collect leftover groups (unmatched pairs and singletons)
        leftover_groups = [pairs[i] for i in range(len(pairs)) if i not in used]

        # Greedy packing of leftovers into rooms, enforcing grade-touch rule
        current = []
        for group in leftover_groups:
            for idx in group:
                # Try to add to current room if it keeps grade constraint
                if len(current) < 4:
                    trial = current + [idx]
                    grades = data.loc[trial, "GradeInt"].tolist()
                    if grades_touch(grades):
                        current = trial
                        continue
                # If we can't add to current, flush it and start a new room
                if current:
                    for s in current:
                        data.loc[s, "Assigned"] = True
                    rooms.append([data.loc[s, "Full Name"] for s in current])
                current = [idx]

        # Flush last partial room, if any
        if current:
            for s in current:
                data.loc[s, "Assigned"] = True
            rooms.append([data.loc[s, "Full Name"] for s in current])

        return rooms

    rooms = []

    # Run pairing and room creation separately for each gender
    for gender in ["Male", "Female"]:
        pairs = make_pairs(gender)
        gender_rooms = combine_pairs_to_rooms(pairs)
        rooms.extend(gender_rooms)

    # Ensure all rooms have exactly 4 "slots" (pad with None if necessary)
    for room in rooms:
        while len(room) < 4:
            room.append(None)

    return rooms

def save_rooms_to_csv(rooms, output_path):
    """Save the room assignments to a CSV file."""
    rooms_df = pd.DataFrame(
        rooms,
        columns=["Roommate 1", "Roommate 2", "Roommate 3", "Roommate 4"]
    )
    rooms_df.to_csv(output_path, index=False)

def main():
    print("Shreya was here :)")
    input_path = "students.csv"  # Path to input CSV file
    output_path = "room_assignments.csv"  # Path to output CSV file

    # Load data
    data = load_data(input_path)

    # Validate required columns
    required_columns = (
        ["Full Name", "Gender", "Grade:"] +
        [f"Request {i}" for i in range(1, 4)]
    )
    if not all(col in data.columns for col in required_columns):
        raise ValueError(
            "The input CSV file must contain the following columns: "
            + ", ".join(required_columns)
        )

    # Create rooms
    rooms = create_rooms(data)

    # Save room assignments to a file
    save_rooms_to_csv(rooms, output_path)
    print(f"Room assignments saved to {output_path}")

if __name__ == "__main__":
    main()
