# Function to check student eligibility
def check_eligibility(percentage):

    # Check if percentage is 60 or above
    if percentage >= 60:
        return "Eligible"

    # If percentage is below 60
    else:
        return "Not Eligible"