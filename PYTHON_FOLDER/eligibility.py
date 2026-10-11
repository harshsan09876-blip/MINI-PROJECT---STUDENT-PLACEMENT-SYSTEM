"""Eligibility verification engine for campus placement drives."""

def check_eligibility(student, drive):
    """
    Check if a student meets all criteria for a specific placement drive.
    Returns: 'Eligible' or 'Not Eligible: <reason>'
    """
    # 1. Backlogs check
    backlogs = int(student.get("backlogs") or 0)
    if backlogs > 0:
        return "Not Eligible: Active backlogs detected"

    criteria_type = drive.get("criteria_type") or drive.get("criteriaType") or "cgpa"
    min_criteria = float(drive.get("minimum_criteria") or drive.get("minimumCriteria") or drive.get("min_cgpa") or drive.get("minCgpa") or 0)

    # 2. Percentage criteria check
    if criteria_type == "percentage":
        student_percentage = float(student.get("percentage") or 0)
        # If student percentage is 0 but CGPA is present, convert CGPA to approximate % (CGPA * 9.5)
        if student_percentage == 0 and student.get("cgpa"):
            student_percentage = float(student.get("cgpa")) * 9.5

        if student_percentage >= min_criteria:
            return "Eligible"
        else:
            return f"Not Eligible: Requires minimum {min_criteria}% (You have {student_percentage:.1f}%)"

    # 3. CGPA criteria check
    elif criteria_type == "cgpa":
        student_cgpa = float(student.get("cgpa") or 0)
        # If student CGPA is 0 but percentage is present, approximate CGPA (Percentage / 9.5)
        if student_cgpa == 0 and student.get("percentage"):
            student_cgpa = round(float(student.get("percentage")) / 9.5, 2)

        if student_cgpa >= min_criteria:
            return "Eligible"
        else:
            return f"Not Eligible: Requires minimum {min_criteria} CGPA (You have {student_cgpa:.1f})"

    # Default fallback
    return "Eligible"
