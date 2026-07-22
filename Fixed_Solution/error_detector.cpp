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
    transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

string toTitleCase(const string& s) {
    string upper = s, lower = s;
    transform(upper.begin(), upper.end(), upper.begin(), ::toupper);
    transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (s != upper && s != lower) return s;
    string result = lower;
    bool cap = true;
    for (size_t i = 0; i < result.size(); i++) {
        if (cap && isalpha(result[i])) {
            result[i] = toupper(result[i]);
            cap = false;
        }
        if (result[i] == ' ' || result[i] == '-') cap = true;
    }
    return result;
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
            int cost = (tolower(a[i-1]) != tolower(b[j-1])) ? 1 : 0;
            dp[i][j] = min({dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost});
        }
    return dp[m][n];
}

string findClosest(const string& name, const set<string>& names, int threshold = 3) {
    string best;
    int bestDist = threshold + 1;
    for (const auto& n : names) {
        int d = levenshtein(toLower(name), toLower(n));
        if (d > 0 && d < bestDist) {
            bestDist = d;
            best = n;
        }
    }
    return best;
}

int main() {
    ifstream regFile("registered.csv");
    if (!regFile.is_open()) { cerr << "Cannot open registered.csv\n"; return 1; }

    set<string> registeredNames;
    map<string, vector<string>> regFirstToFull;
    map<string, vector<string>> regLastToFull;
    set<string> regOrigCase;
    map<string, string> regNameToGrade;
    string line;
    while (getline(regFile, line)) {
        auto fields = parseCSVLine(line);
        if (fields.size() >= 2) {
            string first = trim(fields[0]);
            string last = trim(fields[1]);
            string fullName = first + " " + last;
            string grade = (fields.size() >= 4) ? trim(fields[3]) : "";
            registeredNames.insert(toLower(fullName));
            regFirstToFull[toLower(first)].push_back(fullName);
            regLastToFull[toLower(last)].push_back(fullName);
            regOrigCase.insert(fullName);
            regNameToGrade[toLower(fullName)] = grade;
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
    set<string> fullNames;
    map<string, string> nameToGrade;

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
        students.push_back(s);
    }
    stuFile.close();

    cout << "Student,Row,Request Number,Error Type,Details,Suggested Fix" << endl;

    for (const auto& s : students) {
        if (!s.gender.empty() && s.gender != "Male" && s.gender != "Female") {
            string suggestion = "";
            if (toLower(s.gender).find("fem") != string::npos || toLower(s.gender).find("fem") == 0)
                suggestion = "Female";
            else if (toLower(s.gender).find("mal") != string::npos)
                suggestion = "Male";
            cout << s.fullName << "," << s.rowNum << ",N/A,Invalid Gender,\""
                 << "Gender value is '" << s.gender << "'\",\"" << suggestion << "\"" << endl;
        }

        if (s.legalLast.empty()) {
            string suggested = "";
            size_t sp = s.fullName.find(' ');
            if (sp != string::npos) suggested = s.fullName.substr(sp + 1);
            cout << s.fullName << "," << s.rowNum << ",N/A,Missing Last Name,\""
                 << "Legal Last Name column is empty\",\"" << suggested << "\"" << endl;
        }

        if (!s.legalFirst.empty() && !s.legalLast.empty()) {
            string expected = s.legalFirst + " " + s.legalLast;
            if (toLower(expected) != toLower(s.fullName)) {
                cout << s.fullName << "," << s.rowNum << ",N/A,Name Mismatch,\""
                     << "Full Name '" << s.fullName << "' does not match Legal Name '" << expected
                     << "'\",\"" << expected << "\"" << endl;
            }
        }

        if (registeredNames.find(toLower(s.fullName)) == registeredNames.end()) {
            string suggestion = "";
            string firstName = s.fullName, lastName = "";
            size_t sp = firstName.find(' ');
            if (sp != string::npos) {
                lastName = firstName.substr(sp + 1);
                firstName = firstName.substr(0, sp);
            }

            auto it = regFirstToFull.find(toLower(firstName));
            if (it != regFirstToFull.end() && it->second.size() == 1) {
                suggestion = toTitleCase(it->second[0]);
            } else if (it != regFirstToFull.end() && it->second.size() > 1) {
                set<string> candidates(it->second.begin(), it->second.end());
                suggestion = toTitleCase(findClosest(s.fullName, candidates, 100));
            } else if (!lastName.empty()) {
                auto itL = regLastToFull.find(toLower(lastName));
                if (itL != regLastToFull.end() && itL->second.size() == 1) {
                    suggestion = toTitleCase(itL->second[0]);
                } else if (itL != regLastToFull.end() && itL->second.size() > 1) {
                    set<string> candidates(itL->second.begin(), itL->second.end());
                    suggestion = toTitleCase(findClosest(s.fullName, candidates, 100));
                } else {
                    suggestion = toTitleCase(findClosest(s.fullName, regOrigCase));
                }
            } else {
                suggestion = toTitleCase(findClosest(s.fullName, regOrigCase));
            }
            cout << s.fullName << "," << s.rowNum << ",N/A,Name Not Registered,\""
                 << "'" << s.fullName << "' not found in registered.csv\",\"" << suggestion << "\"" << endl;
        }

        if (!s.numReq.empty()) {
            int n = atoi(s.numReq.c_str());
            if (n < 1 || n > 4) {
                cout << s.fullName << "," << s.rowNum << ",N/A,Invalid Roommate Count,\""
                     << "Requested " << n << " roommates (max 4)\",\"4\"" << endl;
            }
        }

        set<string> seenRequests;
        for (int i = 0; i < 3; i++) {
            if (s.req[i].empty()) continue;

            string reqName = s.req[i];
            int reqNum = i + 1;

            string reqLower = toLower(reqName);
            if (seenRequests.count(reqLower)) {
                cout << s.fullName << "," << s.rowNum << "," << reqNum
                     << ",Duplicate Request,\"'" << reqName << "' appears more than once\",\"Remove duplicate\"" << endl;
                continue;
            }
            seenRequests.insert(reqLower);

            if (toLower(reqName) == toLower(s.fullName)) {
                cout << s.fullName << "," << s.rowNum << "," << reqNum
                     << ",Self Request,\"Student requested themselves\",\"Remove self-request\"" << endl;
                continue;
            }

            if (fullNames.find(reqName) == fullNames.end()) {
                string suggestion = findClosest(reqName, fullNames);
                cout << s.fullName << "," << s.rowNum << "," << reqNum
                     << ",Name Not Found,\"'" << reqName << "' not in student list\",\"" << suggestion << "\"" << endl;
            }

            if (!s.reqGrade[i].empty() && fullNames.find(reqName) != fullNames.end()) {
                string actualGrade = nameToGrade[reqName];
                if (!actualGrade.empty() && s.reqGrade[i] != actualGrade) {
                    cout << s.fullName << "," << s.rowNum << "," << reqNum
                         << ",Grade Mismatch,\"Listed grade " << s.reqGrade[i]
                         << " for '" << reqName << "' but actual grade is " << actualGrade
                         << "\",\"" << actualGrade << "\"" << endl;
                }
            }
        }
    }

    return 0;
}
