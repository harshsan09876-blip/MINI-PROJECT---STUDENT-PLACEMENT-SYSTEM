# Function to check student eligibility
def check_eligibility(student, drive):
    # Invalid or incomplete records should produce an eligibility result rather
    # than raising a TypeError such as "NoneType is not subscriptable".
    if not isinstance(student, dict) or not isinstance(drive, dict):
        return "Criteria Not Available"

    # Check percentage criteria
    criteria_type = drive.get("criteria_type")
    minimum_criteria = drive.get("minimum_criteria")
    if minimum_criteria is None:
        return "Criteria Not Available"

    if criteria_type == "percentage":

        if float(student.get("percentage") or 0) >= float(minimum_criteria):
            return "Eligible"
        else:
            return "Not Eligible"

    # Check CGPA criteria
    elif criteria_type == "cgpa":

        if float(student.get("cgpa") or 0) >= float(minimum_criteria):
            return "Eligible"
        else:
            return "Not Eligible"

    else:
        return "Criteria Not Available"
