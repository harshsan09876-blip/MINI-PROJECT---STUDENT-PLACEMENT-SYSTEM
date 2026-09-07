# Import student data
from student import students

# Import eligibility function
from eligibility import check_eligibility

# Import placement drive data
from placement import placement_drives

# Import test criteria
from test_criteria import test_criteria


# Display project title
print("===== Student Placement System =====")


# Display available placement drives
print("\n----- Placement Drives -----")

# Go through every placement drive
for drive in placement_drives:

    # Get company name
    company = drive["company"]

    # Get job role
    role = drive["role"]

    # Display company and role
    print("\nCompany:", company)
    print("Role:", role)

    # Check if test criteria exists for this company
    if company in test_criteria:

        # Display test eligibility criteria
        print("Test Criteria:", test_criteria[company])

    else:

        # Display message if criteria is not available
        print("Test Criteria: Not Available")