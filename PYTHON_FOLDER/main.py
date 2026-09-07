# Import student data
from student import students

# Import eligibility function
from eligibility import check_eligibility

# Import placement drive data
from placement import placement_drives


# Display project title
print("===== Student Placement System =====")


# Display all students
print("\n----- Students -----")

# Go through each student
for student in students:

    # Check student eligibility
    status = check_eligibility(student["percentage"])

    # Display student details
    print("\nName:", student["name"])
    print("Branch:", student["branch"])
    print("Percentage:", student["percentage"])
    print("Status:", status)


# Display available placement drives
print("\n----- Placement Drives -----")

# Go through each placement drive
for drive in placement_drives:

    # Display company name
    print("\nCompany:", drive["company"])

    # Display job role
    print("Role:", drive["role"])

    # Display eligibility criteria
    print("Criteria:", drive["minimum_criteria"])