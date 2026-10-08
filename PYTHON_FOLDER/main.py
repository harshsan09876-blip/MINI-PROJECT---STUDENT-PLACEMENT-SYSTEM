# Import student data
from student import students

# Import eligibility function
from eligibility import check_eligibility

# Import placement drive data
from placement import placement_drives

# Import test criteria
from test_criteria import test_criteria

# Import company details
from company import company_details


# Display project title
print("===== Student Placement System =====")


# Display available placement drives
print("\n----- Placement Drives -----")

# Go through every placement drive
for drive in placement_drives:

    company = drive["company"]
    role = drive["role"]

    print("\nCompany:", company)
    print("Role:", role)

    if company in test_criteria:
        print("Test Criteria:", test_criteria[company])
    else:
        print("Test Criteria: Not Available")

    if company in company_details:
        print("Test Dates:", company_details[company]["test_dates"])
    else:
        print("Test Dates: Not Available")


# Display student eligibility
print("\n----- Student Eligibility -----")

for student in students:

    print("\nStudent:", student["name"])
    print("Branch:", student["branch"])
    print("Percentage:", student["percentage"])
    print("CGPA:", student["cgpa"])
    print("Backlogs:", student["backlogs"])

    for drive in placement_drives:

        result = check_eligibility(student, drive)

        print(drive["company"], ":", result)