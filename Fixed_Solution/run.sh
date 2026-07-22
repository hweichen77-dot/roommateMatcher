#!/bin/bash
pip3 install pandas openpyxl
chmod 644 students.csv
g++ -o error_detector error_detector.cpp -std=c++17
./error_detector > errors_raw.csv
python3 generate_report.py
python3 fix_errors.py
cp students.csv students_original.csv
cp students_corrected.csv students.csv
python3 roomateMatcher.py
cp students_original.csv students.csv
rm students_original.csv
