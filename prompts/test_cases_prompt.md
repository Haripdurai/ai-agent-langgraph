# Motor Insurance Policy Creation - Test Cases Prompt

You are a senior QA engineer specializing in test case design for motor insurance products.
Generate comprehensive test cases for the motor insurance policy creation feature.

## Motor Insurance Policy Form Fields

The policy creation form includes the following fields:
- **Customer Persona Details**: Name, DOB, Gender, Contact Information
- **Car Registration**: Vehicle Registration Number, Make, Model, Engine Number
- **House Number/Address**: Residential Address for premium calculation
- **Additional Driver(s)**: Information for secondary drivers (optional)
- **Policy Start Date**: Date when coverage begins (cannot be a past date)
- **Previous Claims**: Number and details of previous insurance claims
- **Convictions**: Traffic violations and convictions history
- **Claims/Convictions Eligibility**: Policy availability with or without previous claims/convictions

## Critical Validation Rules

1. **Policy Start Date Validation**: 
   - Customer CANNOT select a past date for policy start
   - Must be today's date or any future date
   - Show error message for past dates

2. **Required Field Validation**: All mandatory fields must be filled
3. **Data Format Validation**: Phone numbers, registration numbers must match expected formats
4. **Age Validation**: Driver must be minimum 18 years old
5. **Car Age Validation**: Vehicle should not be older than 20 years

## Test Case Categories

1. **Positive Test Cases**: Valid policies creation with complete and accurate information
2. **Negative Test Cases**: Invalid inputs, missing fields, and error scenarios (especially past date validation)
3. **Edge Case Test Cases**: Boundary conditions, limit testing, and special scenarios

## Test Case Format

For each test case, include:
- **Test Case ID** (e.g., TC001, TC002)
- **Title**: Brief description
- **Preconditions**: What must be true before executing (e.g., user on policy creation page)
- **Steps**: Numbered action steps (explicit form field values)
- **Expected Result**: What should happen
- **Priority**: High/Medium/Low

## Requirements

- Format each test case clearly with sections separated by dashes (---)
- **IMPORTANT**: Include at least 2-3 test cases specifically for past date validation in Policy Start Date
- Include test cases for customers with previous claims vs without previous claims
- Include test cases for additional drivers (with and without)
- Aim for 4-5 positive cases, 4-5 negative cases (including past date tests), and 3-4 edge cases
- Return only the test cases – no introduction or closing text
- Use clear, concise language with specific form field values
- Test cases should be independent and executable in any order

## Issue Details

**Issue Key**: {key}

**Summary**: {summary}

**Description**: {description}
