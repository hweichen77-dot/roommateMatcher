# Roommate Matcher

> **This is not a new project.** It is a copy of [natmkk/roommateMatcher](https://github.com/natmkk/roommateMatcher), published here so my own contributions to it are readable in one place. The matcher was written by Grace Xu and allisonlao, with later additions by natmkk. My work was done in March 2026 in my fork of that repository, before this copy existed, so the commit history here is just the import and does not reflect when the work happened. What I added is described under [What I contributed](#what-i-contributed).

Roommate assignment for DECA conferences. Students submit a form listing who they want to room with, and the matcher groups them into rooms of four while respecting grade and gender constraints.

The problem is that the form responses are messy. Students misspell each other's names, list a grade that does not match the roster, request themselves, or fill in a name that belongs to nobody. The matcher assumes clean input, so a single typo silently drops a student out of their group.

This repository adds a validation stage that runs before the matcher, catches those problems, reports them in a spreadsheet an adviser can read, and applies the safe corrections automatically.

## What I contributed

The matcher itself was written by Grace Xu and allisonlao, with later additions by natmkk. My work is the `Fixed_Solution/` directory, about 1,100 lines across nine files, which I committed to my fork of [natmkk/roommateMatcher](https://github.com/natmkk/roommateMatcher) on March 20 and 21, 2026. That fork is where the real history and dates live. This copy came later and exists only to make the work readable.

To be clear about the boundary: `Fixed_Solution/roomateMatcher.py` and `Fixed_Solution/validation.py` are unmodified copies of the original authors' files, included so the folder runs on its own. Everything else in that directory is mine.

### The error detector (`error_detector.cpp`, 297 lines)

A C++ program that cross-references the form responses in `students.csv` against the official roster in `registered.csv` and writes one row per problem, each with a suggested correction. It checks for nine things:

- a gender value that is not Male or Female, with the intended value guessed from the prefix
- an empty legal last name, filled in from the full name
- a full name that disagrees with the legal first and last name columns
- a name that does not appear on the roster at all
- a requested roommate count outside 1 to 4
- the same person requested twice
- a student requesting themselves
- a requested roommate who is not in the student list
- a listed grade that disagrees with the roster's grade for that person

The suggestions are the part that took the most work. When a name does not match, the program finds the closest roster entry by Levenshtein distance, but a plain distance search over 190 names produces bad guesses. So it first tries an exact first-name index, then an exact last-name index, and only falls back to a full fuzzy search when neither is unique. That way "Alysas Ho" resolves to "Alyssa Ho" through the last name rather than to whichever roster entry happens to be three edits away.

Getting real form data to parse also meant handling things the standard tools do not. The CSV parser tracks quote state so that quoted fields containing commas stay intact, and the cleaner strips non-breaking spaces, which is what you get when a student pastes a name out of a Google Doc and which otherwise makes two identical-looking names compare as different.

### The report (`generate_report.py`, 33 lines)

The detector writes raw CSV, which is fine for the next program and unpleasant for a person. This turns it into `error_report.xlsx` with bold headers and column widths set so the details column is actually readable, since the adviser fixing these rows is not going to work from a terminal.

### The corrector (`fix_errors.py`, 179 lines)

Reads the detected errors back in and applies the fixes to produce `students_corrected.csv`. It writes to a new file and leaves the original untouched, so a wrong automatic correction can never destroy the submitted data.

### The runner and the instructions (`run.sh`, `How_to_run_everything.txt`)

`run.sh` chains the whole thing: compile the detector, run it, build the report, apply the fixes, swap the corrected file in, run the matcher, then put the original file back. The instructions file is written for teammates who had not used a terminal before, so it starts from how to open Terminal and how to install a compiler.

### A note on the data in this repository

The input files here are generated sample data. The real conference ran on forms containing student names, school email addresses, and student ID numbers, none of which are published here.

The sample roster is built to behave like the real one. It has the same row counts, the same deliberately seeded mistakes, and the same relationships between the roster and the form responses, including the misspelled email domains that appear in the real file. Running the detector against it produces 39 errors across all 8 categories, which matches the real data exactly.

## Running it

You need `g++` and Python 3 with `pandas` and `openpyxl`.

```bash
cd Fixed_Solution
chmod +x run.sh
./run.sh
```

That produces four files:

- `errors_raw.csv`, the detected errors
- `error_report.xlsx`, the readable version of the same
- `students_corrected.csv`, the form data with fixes applied
- `room_assignments.csv`, the final room groupings

`How_to_run_everything.txt` covers the same steps in more detail, including installation, for anyone who has not done this before.
