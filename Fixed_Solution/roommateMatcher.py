import pandas as pd
from itertools import combinations
import os
import time
import numpy as np

def load_data(file_path):
    """Load the student data and convert N/A placeholders into true blank/NaN values."""
    df = pd.read_csv(file_path)
    placeholders = ["N/A", "n/a", "NA", "na", "None", "none",]
    df.replace(placeholders, np.nan, inplace=True)
    return df

def grades_touch(grades):
    """
    Return True if the distinct grades form a contiguous sequence.
    e.g. [9,10], [10,11], [9,10,11] are OK; [9,11] is not.
    """
    g = sorted(set(int(x) for x in grades if pd.notna(x)))
    if not g:
        return True
    return g[-1] - g[0] + 1 == len(g)

from math import ceil

def create_rooms(data):
    """
    Per gender: R = ceil(n/4) rooms, E = 4R - n empty slots.
    Priority:
      1. Mutual groups of 4
      2. Two mutual pairs combined into a room
      3. Mutual groups of 3
      4. Individuals fill the gaps (request links preferred, then closest grade)
      5. Last resort: split mutual 3-groups (a mutual pair inside is kept together)
    Grade-touch is required for every mutual group and every combined room.
    """
    from collections import Counter

    data = data.copy()
    if "Grade:" not in data.columns:
        raise ValueError("Input CSV must contain a 'Grade:' column for student grade.")
    data["GradeInt"] = data["Grade:"].astype(int)
    data["NormalizedName"] = data["Full Name"].astype(str).str.strip().str.lower()

    invalid = {"n/a", "na", "none", "-", "nan", ""}

    def get_requests(idx):
        reqs = set()
        for i in range(1, 4):
            val = data.loc[idx].get(f"Request {i}")
            if isinstance(val, str):
                c = val.strip().lower()
                if c and c not in invalid:
                    reqs.add(c)
        return reqs

    norm = lambda i: data.loc[i, "NormalizedName"]
    full = lambda i: data.loc[i, "Full Name"]
    grade = lambda i: data.loc[i, "GradeInt"]
    fits = lambda g: len(g) <= 4 and grades_touch([grade(i) for i in g])

    all_rooms = []

    for gender in sorted(data["Gender"].dropna().unique()):
        idxs = list(data.index[data["Gender"] == gender])
        n = len(idxs)
        R = ceil(n / 4)
        E = 4 * R - n
        print(f"\n{gender}: {n} students -> {R} rooms, {E} empty slot(s) total")

        reqs = {i: get_requests(i) for i in idxs}
        unassigned = set(idxs)

        def is_mutual(combo):
            names = {norm(i) for i in combo}
            return all((names - {norm(i)}) <= reqs[i] for i in combo)

        def find_mutual(size):
            found = []
            cands = [i for i in sorted(unassigned) if len(reqs[i]) >= size - 1]
            for combo in combinations(cands, size):
                if all(i in unassigned for i in combo) and is_mutual(combo) and fits(list(combo)):
                    found.append(list(combo))
                    unassigned.difference_update(combo)
                    print(f"  -> Seed group of {size} (not a final room yet): {[full(i) for i in combo]}")
            return found

        def link_score(room, s):
            names = {norm(m) for m in room}
            return (1 if reqs[s] & names else 0) + (1 if any(norm(s) in reqs[m] for m in room) else 0)

        def gap(room, s):
            return abs(grade(s) - sum(grade(m) for m in room) / len(room))

         # Keep everyone linked by mutual requests together (components of size 2-4)
        name_to_i = {norm(i): i for i in idxs}
        mut = {i: {name_to_i[r] for r in reqs[i]
                   if r in name_to_i and norm(i) in reqs[name_to_i[r]]}
               for i in idxs}

        fours, threes, twos = [], [], []
        seen = set()
        for i in idxs:
            if i in seen or not mut[i]:
                continue
            comp, stack = [], [i]
            seen.add(i)
            while stack:
                x = stack.pop()
                comp.append(x)
                for y in mut[x]:
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
            if 2 <= len(comp) <= 4 and fits(comp):
                comp.sort()
                {4: fours, 3: threes, 2: twos}[len(comp)].append(comp)
                unassigned.difference_update(comp)
                print(f"  -> Seed group of {len(comp)} (linked by mutual requests): {[full(i) for i in comp]}")

        # Components too big (5+) or with non-touching grades: fall back to exact mutual groups
        fours += find_mutual(4)
        threes += find_mutual(3)
        twos += find_mutual(2)

        rooms = [{"m": g, "trio": False, "cap": 4} for g in fours]

        # 2. Combine mutual pairs (closest grades first, grades must touch)
        pairs_left = list(twos)
        while pairs_left:
            p = pairs_left.pop(0)
            p_avg = sum(grade(i) for i in p) / 2
            for q in sorted(pairs_left, key=lambda q: abs(p_avg - sum(grade(i) for i in q) / 2)):
                if fits(p + q):
                    pairs_left.remove(q)
                    rooms.append({"m": p + q, "trio": False, "cap": 4})
                    print(f"  -> Combined pairs: {[full(i) for i in p + q]}")
                    break
            else:
                rooms.append({"m": p, "trio": False, "cap": 4})  # lone pair, gets individuals

        # 3. Mutual trios
        rooms += [{"m": t, "trio": True, "cap": 4} for t in threes]

        # Too many seeded rooms for R? Merge lone pairs first, then split trios.
        while len(rooms) > R:
            # a) merge two lone pairs if their grades touch
            lone = [r for r in rooms if len(r["m"]) == 2]
            merged = False
            for a in lone:
                for b in lone:
                    if a is not b and fits(a["m"] + b["m"]):
                        rooms.remove(b)
                        a["m"] = a["m"] + b["m"]
                        print(f"  -> Merged two pairs: {[full(i) for i in a['m']]}")
                        merged = True
                        break
                if merged:
                    break
            if merged:
                continue

            # b) split a mutual trio (trios with no mutual pair inside go first)
            trios_ = [r for r in rooms if r["trio"]]
            if trios_:
                trios_.sort(key=lambda r: any(is_mutual(c) for c in combinations(r["m"], 2)))
                v = trios_[0]
                rooms.remove(v)
                kept = None
                for a, b in combinations(v["m"], 2):
                    if is_mutual((a, b)):
                        kept = [a, b]
                        break
                if kept:
                    rooms.append({"m": kept, "trio": False, "cap": 4})
                    unassigned.update(i for i in v["m"] if i not in kept)
                    print(f"  -> Split 3-group, kept mutual pair together: {[full(i) for i in kept]}")
                else:
                    unassigned.update(v["m"])
                    print(f"  -> Split up 3-group (last resort): {[full(i) for i in v['m']]}")
                continue

            print(f"  WARNING: {len(rooms)} rooms needed but only {R} allowed for {gender}.")
            break

        # Too few rooms? Seed new ones from individuals, spread across grades.
        need = R - len(rooms)
        if need > 0 and unassigned:
            singles = sorted(unassigned, key=lambda s: (grade(s), s))
            need = min(need, len(singles))
            seeds = [singles[int(k * len(singles) / need)] for k in range(need)]
            for s in seeds:
                unassigned.remove(s)
                rooms.append({"m": [s], "trio": False, "cap": 4})

                # Fill: every room starts with capacity 4, and the empty slots are whatever is left over.
        # The most constrained individual goes first, so nobody gets stranded.
        # Mutual trios are filled last, so they are the rooms most likely to keep an empty slot.
        def legal_rooms(s):
            return [r for r in rooms if len(r["m"]) < 4 and fits(r["m"] + [s])]

        while unassigned:
            options = {s: legal_rooms(s) for s in unassigned}
            stuck = [s for s in sorted(unassigned) if not options[s]]
            if stuck:
                s = stuck[0]
                open_ = [r for r in rooms if len(r["m"]) < 4]
                if not open_:
                    print(f"  WARNING: no open room left for {full(s)}")
                    unassigned.remove(s)
                    continue
                r = min(open_, key=lambda r: gap(r["m"], s))
                print(f"  WARNING: grade rule broken placing {full(s)} with {[full(i) for i in r['m']]}")
            else:
                s = min(unassigned, key=lambda x: (len(options[x]), x))
                r = max(options[s], key=lambda r: (link_score(r["m"], s), not r["trio"], len(r["m"]), -gap(r["m"], s)))
            r["m"].append(s)
            unassigned.remove(s)

        all_rooms += [r["m"] for r in rooms]
 # ---- audit: mutual groups that ended up apart ----
    room_of = {i: k for k, room in enumerate(all_rooms, 1) for i in room}
    all_reqs = {i: get_requests(i) for i in data.index}
    name_to_i = {norm(i): i for i in data.index}
    mut = {}
    for i in data.index:
        mut[i] = {name_to_i[r] for r in all_reqs[i]
                  if r in name_to_i and norm(i) in all_reqs[name_to_i[r]]}

    print("\nAUDIT: mutual groups not kept together")
    seen, bad = set(), 0
    for size in (4, 3, 2):
        for i in data.index:
            for others in combinations(sorted(mut[i]), size - 1):
                grp = tuple(sorted((i,) + others))
                if grp in seen:
                    continue
                if all(set(grp) - {j} <= mut[j] for j in grp) and fits(list(grp)):
                    seen.add(grp)
                    if len({room_of[j] for j in grp}) > 1:
                        bad += 1
                        print(f"  Mutual {size}-group split:")
                        for j in grp:
                            print(f"    {full(j)} (grade {grade(j)}, {data.loc[j, 'Gender']}) -> room {room_of[j]}, "
                                  f"{len(mut[j])} mutual partner(s)")
    if bad == 0:
        print("  none")
    # ---- final report ----
    sizes = Counter(len(room) for room in all_rooms)
    print("\nFINAL ROOMS:")
    for k, room in enumerate(all_rooms, 1):
        print(f"  Room {k} ({len(room)}/4): {[full(i) for i in room]}")
    print(f"\nRoom size counts: {dict(sorted(sizes.items(), reverse=True))}")

    

    return [[full(i) for i in room] + [None] * (4 - len(room)) for room in all_rooms]
    
def save_rooms_to_csv(rooms, output_path):
    """Save the room assignments to a CSV file."""
    rooms_df = pd.DataFrame(
        rooms,
        columns=["Roommate 1", "Roommate 2", "Roommate 3", "Roommate 4"]
    )
    
    target_path = output_path
    try:
        rooms_df.to_csv(target_path, index=False)
    except PermissionError:
        timestamp = int(time.time())
        base, ext = os.path.splitext(output_path)
        target_path = f"{base}_{timestamp}{ext}"
        rooms_df.to_csv(target_path, index=False)
        print(f"\n[WARNING] 'room_assignments.csv' was locked. Saved as: {target_path}")
        return

    print(f"\nSUCCESS: Room assignments saved to {target_path}")

def main():
    print("Shreya was here :)")
    print("Sophie was here too! :D")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "students_corrected.csv") 
    output_path = os.path.join(script_dir, "room_assignments.csv")

    try:
        data = load_data(input_path)

        required_columns = (
            ["Full Name", "Gender", "Grade:"] +
            [f"Request {i}" for i in range(1, 4)]
        )
        if not all(col in data.columns for col in required_columns):
            raise ValueError(
                "The input CSV file must contain the following columns: "
                + ", ".join(required_columns)
            )

        rooms = create_rooms(data)
        save_rooms_to_csv(rooms, output_path)
        
    except Exception as e:
        print(f"\n[ERROR]: The script stopped because of this: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL CRASH]: {e}")
    
    input("\nProgram finished. Press Enter to exit...")
