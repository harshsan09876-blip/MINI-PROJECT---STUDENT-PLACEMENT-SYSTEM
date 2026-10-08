# Function to check student eligibility
def check_eligibility(student, drive):

    # Check percentage criteria
    if drive["criteria_type"] == "percentage":

        if student["percentage"] >= drive["minimum_criteria"]:
            return "Eligible"
        else:
            return "Not Eligible"

    # Check CGPA criteria
    elif drive["criteria_type"] == "cgpa":

        if student["cgpa"] >= drive["minimum_criteria"]:
            return "Eligible"
        else:
            return "Not Eligible"

    else:
        return "Criteria Not Available"