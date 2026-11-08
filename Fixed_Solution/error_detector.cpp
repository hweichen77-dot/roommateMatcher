#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <set>
#include <map>
#include <algorithm>
#include <cctype>

using namespace std;

string replaceNbsp(const string& s) {
    string result;
    for (size_t i = 0; i < s.size(); i++) {
        if (i + 1 < s.size() && (unsigned char)s[i] == 0xC2 && (unsigned char)s[i+1] == 0xA0) {
            result += ' ';
            i++;
        } else {
            result += s[i];
        }
    }
    return result;
}

string trim(const string& s) {
    string cleaned = replaceNbsp(s);
    size_t start = cleaned.find_first_not_of(" \t\r\n");
    if (start == string::npos) return "";
    size_t end = cleaned.find_last_not_of(" \t\r\n");
    return cleaned.substr(start, end - start + 1);
}

string toLower(string s) {
    transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return tolower(c); });
    return s;
}

// Collapse runs of whitespace into a single space (after trimming).
string collapseSpaces(const string& s) {
    string t = trim(s);
    string out;
    bool prevSpace = false;
    for (char c : t) {
        if (c == ' ' || c == '\t') {
            if (!prevSpace) out += ' ';
            prevSpace = true;
        } else {
            out += c;
            prevSpace = false;
        }
    }
    return out;
}

// Normalized comparison key: lowercase, single spaces, no nbsp.
string key(const string& s) {
    return toLower(collapseSpaces(s));
}

string toTitleCase(const string& s) {
    string upper = s, lower = s;
    transform(upper.begin(), upper.end(), upper.begin(), [](unsigned char c) { return toupper(c); });
    transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return tolower(c); });
    if (s != upper && s != lower) return s;
    string result = lower;
    bool cap = true;
    for (size_t i = 0; i < result.size(); i++) {
        if (cap && isalpha((unsigned char)result[i])) {
            result[i] = toupper((unsigned char)result[i]);
            cap = false;
        }
        if (result[i] == ' ' || result[i] == '-') cap = true;
    }
    return result;
}

// Wrap a value in quotes and double any inner quotes so the CSV stays valid.
string q(const string& s) {
    string r = "\"";
    for (char c : s) {
        if (c == '"') r += "\"\"";
        else r += c;
    }
    r += "\"";
    return r;
}

void emit(const string& student, int row, const string& reqNum, const string& type,
          const string& details, const string& fix) {
    cout << q(student) << "," << row << "," << reqNum << "," << type << ","
         << q(details) << "," << q(fix) << endl;
}

vector<string> parseCSVLine(const string& line) {
    vector<string> fields;
    string field;
    bool inQuotes = false;
    for (size_t i = 0; i < line.size(); i++) {
        char c = line[i];
        if (c == '"') {
            inQuotes = !inQuotes;
        } else if (c == ',' && !inQuotes) {
            fields.push_back(trim(field));
            field.clear();
        } else {
            field += c;
        }
    }
    fields.push_back(trim(field));
    return fields;
}

int levenshtein(const string& a, const string& b) {
    int m = a.size(), n = b.size();
    vector<vector<int>> dp(m + 1, vector<int>(n + 1));
    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;
    for (int i = 1; i <= m; i++)
        for (int j = 1; j <= n; j++) {
            int cost = (tolower((unsigned char)a[i-1]) != tolower((unsigned char)b[j-1])) ? 1 : 0;
            dp[i][j] = min({dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost});
        }
    return dp[m][n];
}

string findClosest(const string& name, const set<string>& names, int threshold = 3) {
    string best;
    int bestDist = threshold + 1;
    string nk = key(name);
    for (const auto& n : names) {
        int d = levenshtein(nk, key(n));
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = n;
        }
    }
    return best;
}

// Reads the first run of digits (e.g. "3 (including myself)" -> 3, "9.0" -> 9). 0 if none.
int parseLeadingNumber(const string& s) {
    size_t i = 0;
    while (i < s.size() && !isdigit((unsigned char)s[i])) i++;
    if (i == s.size()) return 0;
    int value = 0;
    while (i < s.size() && isdigit((unsigned char)s[i])) {
        value = value * 10 + (s[i] - '0');
        if (value > 1000) break;
        i++;
    }
    return value;
}

int main() {
    ifstream regFile("registered.csv");
    if (!regFile.is_open()) { cerr << "Cannot open registered.csv\n"; return 1; }

    set<string> registeredNames;                  // normalized keys
    map<string, vector<string>> regFirstToFull;   // key(first) -> full names
    map<string, vector<string>> regLastToFull;    // key(last)  -> full names
    set<string> regOrigCase;
    string line;
    while (getline(regFile, line)) {
        auto fields = parseCSVLine(line);
        if (fields.size() >= 2) {
            string first = collapseSpaces(fields[0]);
            string last = collapseSpaces(fields[1]);
            string fullName = first + " " + last;
            registeredNames.insert(key(fullName));
            regFirstToFull[key(first)].push_back(fullName);
            regLastToFull[key(last)].push_back(fullName);
            regOrigCase.insert(fullName);
        }
    }
    regFile.close();

    ifstream stuFile("students.csv");
    if (!stuFile.is_open()) { cerr << "Cannot open students.csv\n"; return 1; }

    getline(stuFile, line);
    auto header = parseCSVLine(line);

    map<string, int> colIdx;
    for (int i = 0; i < (int)header.size(); i++) colIdx[header[i]] = i;

    int colFullName = colIdx["Full Name"];
    int colLegalFirst = colIdx["Legal First Name"];
    int colLegalLast = colIdx["Legal Last Name"];
    int colGrade = colIdx["Grade:"];
    int colGender = colIdx["Gender"];
    int colNumReq = colIdx["Number of Requested Roommates (including yourself):"];
    int colReq1 = colIdx["Request 1"];
    int colReq1Grade = colIdx["Roommate 1's Grade:"];
    int colReq2 = colIdx["Request 2"];
    int colReq2Grade = colIdx["Roommate 2's Grade:"];
    int colReq3 = colIdx["Request 3"];
    int colReq3Grade = colIdx["Roommate 3's Grade:"];

    struct StudentRow {
        string fullName, legalFirst, legalLast, grade, gender, numReq;
        string req[3], reqGrade[3];
        int rowNum;
    };

    vector<StudentRow> students;
    set<string> fullNames;                 // exact stored names
    map<string, string> nameToGrade;       // exact name -> grade
    map<string, string> keyToName;         // normalized key -> stored name

    int rowNum = 1;
    while (getline(stuFile, line)) {
        rowNum++;
        auto f = parseCSVLine(line);
        if ((int)f.size() <= colFullName) continue;

        auto getF = [&](int idx) -> string {
            return (idx >= 0 && idx < (int)f.size()) ? f[idx] : "";
        };

        StudentRow s;
        s.rowNum = rowNum;
        s.fullName = getF(colFullName);
        s.legalFirst = getF(colLegalFirst);
        s.legalLast = getF(colLegalLast);
        s.grade = getF(colGrade);
        s.gender = getF(colGender);
        s.numReq = getF(colNumReq);
        s.req[0] = getF(colReq1);   s.reqGrade[0] = getF(colReq1Grade);
        s.req[1] = getF(colReq2);   s.reqGrade[1] = getF(colReq2Grade);
        s.req[2] = getF(colReq3);   s.reqGrade[2] = getF(colReq3Grade);

        fullNames.insert(s.fullName);
        nameToGrade[s.fullName] = s.grade;
        if (!keyToName.count(key(s.fullName))) keyToName[key(s.fullName)] = s.fullName;
        students.push_back(s);
    }
    stuFile.close();

    cout << "Student,Row,Request Number,Error Type,Details,Suggested Fix" << endl;

    for (const auto& s : students) {
        if (!s.gender.empty() && s.gender != "Male" && s.gender != "Female") {
            string suggestion = "";
            string g = toLower(s.gender);
            if (g.find("fem") != string::npos)
                suggestion = "Female";
            else if (g.find("mal") != string::npos)
                suggestion = "Male";
            emit(s.fullName, s.rowNum, "N/A", "Invalid Gender",
                 "Gender value is '" + s.gender + "'", suggestion);
        }

        if (s.legalLast.empty()) {
            string suggested = "";
            size_t sp = s.fullName.find(' ');
            if (sp != string::npos) suggested = s.fullName.substr(sp + 1);
            emit(s.fullName, s.rowNum, "N/A", "Missing Last Name",
                 "Legal Last Name column is empty", suggested);
        }

        if (!s.legalFirst.empty() && !s.legalLast.empty()) {
            string expected = s.legalFirst + " " + s.legalLast;
            if (key(expected) != key(s.fullName)) {
                emit(s.fullName, s.rowNum, "N/A", "Name Mismatch",
                     "Full Name '" + s.fullName + "' does not match Legal Name '" + expected + "'",
                     expected);
            }
        }

        if (registeredNames.find(key(s.fullName)) == registeredNames.end()) {
            string suggestion = "";
            string clean = collapseSpaces(s.fullName);
            string firstName = clean, lastName = "";
            size_t sp = firstName.find(' ');
            if (sp != string::npos) {
                lastName = firstName.substr(sp + 1);
                firstName = firstName.substr(0, sp);
            }

            auto it = regFirstToFull.find(key(firstName));
            if (it != regFirstToFull.end() && it->second.size() == 1) {
                suggestion = toTitleCase(it->second[0]);
            } else if (it != regFirstToFull.end() && it->second.size() > 1) {
                set<string> candidates(it->second.begin(), it->second.end());
                suggestion = toTitleCase(findClosest(clean, candidates, 100));
            } else if (!lastName.empty()) {
                auto itL = regLastToFull.find(key(lastName));
                if (itL != regLastToFull.end() && itL->second.size() == 1) {
                    suggestion = toTitleCase(itL->second[0]);
                } else if (itL != regLastToFull.end() && itL->second.size() > 1) {
                    set<string> candidates(itL->second.begin(), itL->second.end());
                    suggestion = toTitleCase(findClosest(clean, candidates, 100));
                } else {
                    suggestion = toTitleCase(findClosest(clean, regOrigCase));
                }
            } else {
                suggestion = toTitleCase(findClosest(clean, regOrigCase));
            }
            emit(s.fullName, s.rowNum, "N/A", "Name Not Registered",
                 "'" + s.fullName + "' not found in registered.csv", suggestion);
        }

        // Roommate count: only flag if the first number in the cell is not 1-4.
        // Suggested fix = the student plus each non-empty request.
        if (!s.numReq.empty()) {
            int n = parseLeadingNumber(s.numReq);
            if (n < 1 || n > 4) {
                int actual = 1;
                for (int i = 0; i < 3; i++) {
                    if (!s.req[i].empty()) actual++;
                }
                emit(s.fullName, s.rowNum, "N/A", "Invalid Roommate Count",
                     "Requested " + to_string(n) + " roommates (max 4)", to_string(actual));
            }
        }

        set<string> seenRequests;
        for (int i = 0; i < 3; i++) {
            if (s.req[i].empty()) continue;

            string reqName = s.req[i];
            string reqNum = to_string(i + 1);
            string rk = key(reqName);

            if (seenRequests.count(rk)) {
                emit(s.fullName, s.rowNum, reqNum, "Duplicate Request",
                     "'" + reqName + "' appears more than once", "Remove duplicate");
                continue;
            }
            seenRequests.insert(rk);

            if (rk == key(s.fullName)) {
                emit(s.fullName, s.rowNum, reqNum, "Self Request",
                     "Student requested themselves", "Remove self-request");
                continue;
            }

            // Exact match required, since fix_errors.py and the room script compare names.
            // If it only matches after normalizing (case / spacing), flag it and suggest the
            // student's stored name so fix_errors.py rewrites the request to match exactly.
            if (fullNames.find(reqName) == fullNames.end()) {
                string suggestion;
                auto kn = keyToName.find(rk);
                if (kn != keyToName.end()) suggestion = kn->second;
                else suggestion = findClosest(reqName, fullNames);
                emit(s.fullName, s.rowNum, reqNum, "Name Not Found",
                     "'" + reqName + "' not in student list", suggestion);
            }

            // Grade mismatch: compare as numbers so "9" and "9.0" count as equal.
            string lookupName = reqName;
            if (fullNames.find(lookupName) == fullNames.end()) {
                auto kn = keyToName.find(rk);
                if (kn != keyToName.end()) lookupName = kn->second;
            }
               if (!s.reqGrade[i].empty() && fullNames.find(lookupName) != fullNames.end()) {
                string actualGrade = nameToGrade[lookupName];
                if (!actualGrade.empty() &&
                    parseLeadingNumber(s.reqGrade[i]) != parseLeadingNumber(actualGrade)) {
                    emit(s.fullName, s.rowNum, reqNum, "Grade Mismatch",
                         "Listed grade " + s.reqGrade[i] + " for '" + reqName +
                         "' but actual grade is " + actualGrade,
                         actualGrade);
                }
            }
        }
    }

    return 0;
}
