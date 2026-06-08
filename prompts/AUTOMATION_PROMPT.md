# LLM Prompt: Generate Playwright Java Automation Scripts from Manual Test Cases

## 🎯 OBJECTIVE
You are an expert test automation engineer. Your task is to analyze manual test cases and generate complete, production-ready Playwright Java automation scripts following the existing framework architecture, coding conventions, and design patterns.

**⚠️ CRITICAL: Only use methods that exist in the actual codebase. Every method referenced below has been verified against the source code. Do NOT invent methods that do not exist.**

---

## 📋 PROJECT CONTEXT

### Technology Stack
- **Language**: Java 17
- **Automation Framework**: Playwright Java (version 1.41.0)
- **Test Framework**: TestNG (version 7.9.0)
- **Assertion Library**: AssertJ (version 3.25.1)
- **Build Tool**: Maven
- **Design Pattern**: Page Object Model (POM)
- **Data Management**: Builder Pattern with Lombok
- **Base Test Class**: `com.esure.insurance.base.BaseTest` (ALL test classes MUST extend this)

### Application Under Test
**Esure Motor Insurance Portal** - A web application for creating motor insurance policies with the following workflow:
1. Home Page → Get Quote
2. Customer Details Page → Enter personal information
3. Vehicle Details Page → Enter/lookup vehicle information
4. Cover Selection Page → Select cover type and add-ons
5. Policy Review Page → Review and confirm details
6. Policy Confirmation Page → View created policy

### ⚡ CRITICAL REQUIREMENTS
1. **ALL generated test classes MUST extend `BaseTest`** to inherit:
   - `protected Page page` — Playwright Page instance
   - `protected Browser browser` — Browser instance
   - `protected BrowserContext context` — Browser context
   - `protected ConfigManager config` — Configuration access
   - `protected void takeScreenshot(String name)` — Screenshot utility
   - `protected void navigateToBaseUrl()` — Navigate to base URL
   - `@BeforeMethod setup()` / `@AfterMethod teardown()` — Lifecycle

2. **Use `page` (NOT `this.page`)** when passing to page object constructors:
   ```java
   HomePage homePage = new HomePage(page);  // ✅ Correct
   ```

---

## 🏗️ FRAMEWORK ARCHITECTURE

### Project Structure
```
src/
├── main/java/com/esure/insurance/
│   ├── config/
│   │   └── ConfigManager.java          # Singleton config management
│   ├── models/
│   │   ├── Customer.java               # Customer data model (@Data @Builder)
│   │   ├── Vehicle.java                # Vehicle data model (@Data @Builder)
│   │   └── Policy.java                 # Policy + CoverType/PolicyStatus/AddOn enums
│   ├── pages/
│   │   ├── BasePage.java               # Abstract base with common methods
│   │   ├── HomePage.java               # Home/landing page
│   │   ├── CustomerDetailsPage.java    # Customer details form
│   │   ├── VehicleDetailsPage.java     # Vehicle details form
│   │   ├── CoverSelectionPage.java     # Cover type, add-ons, premium calc
│   │   ├── PolicyReviewPage.java       # Review all details before confirm
│   │   └── PolicyConfirmationPage.java # Success page after policy creation
│   └── utils/
│       └── TestDataBuilder.java        # Test data factory methods
│
└── test/java/com/esure/insurance/
    ├── base/
    │   └── BaseTest.java               # Setup/teardown, provides `page`
    └── tests/
        └── PolicyCreationTests.java    # Existing test scenarios
```

---

## 📝 DATA MODELS (Exact from source)

### Customer Model
```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class Customer {
    private String title;           // Mr, Mrs, Ms, Miss, Dr
    private String firstName;
    private String lastName;
    private LocalDate dateOfBirth;
    private String email;
    private String phoneNumber;
    private String addressLine1;
    private String addressLine2;    // Optional
    private String city;
    private String postcode;
    private String occupation;
    private String licenseNumber;
    private int yearsLicenseHeld;

    // Additional methods:
    public String getFullName();       // returns "title firstName lastName"
    public String getFullAddress();    // returns formatted address string
}
```

### Vehicle Model
```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class Vehicle {
    private String registrationNumber;
    private String make;
    private String model;
    private int year;
    private String fuelType;        // Petrol, Diesel, Electric, Hybrid
    private int engineSize;
    private String color;
    private int numberOfDoors;
    private String transmissionType; // Manual, Automatic
    private boolean isModified;
    private String parkingLocation;  // Driveway, Garage, Street
    private int estimatedAnnualMileage;

    // Additional methods:
    public String getVehicleDescription();  // returns "year make model"
}
```

### Policy Model
```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class Policy {
    private String policyNumber;
    private Customer customer;
    private Vehicle vehicle;
    private CoverType coverType;
    @Builder.Default
    private List<AddOn> addOns = new ArrayList<>();
    private LocalDate startDate;
    private LocalDate endDate;
    private double premium;
    private PolicyStatus status;
    private LocalDate createdDate;

    // Methods:
    public double calculateTotalPremium();  // premium + sum of addOn prices
    public void addAddOn(AddOn addOn);
    public void removeAddOn(AddOn addOn);

    public enum CoverType {
        COMPREHENSIVE("Comprehensive"),
        TPFT("Third Party, Fire and Theft"),
        TPO("Third Party Only");
        public String getDisplayName();
    }

    public enum PolicyStatus {
        DRAFT, ACTIVE, PENDING, CANCELLED, EXPIRED
    }

    public enum AddOn {
        BREAKDOWN_COVER("Breakdown Cover", 50.00),
        LEGAL_COVER("Legal Cover", 25.00),
        COURTESY_CAR("Courtesy Car", 35.00),
        PROTECTED_NO_CLAIMS("Protected No Claims Bonus", 40.00),
        KEY_COVER("Key Cover", 15.00);
        public String getDisplayName();
        public double getPrice();
    }
}
```

---

## 🔧 PAGE OBJECT API REFERENCE (Exact methods from source code)

### BasePage (abstract — all pages inherit these)
```java
// Constructor
public BasePage(Page page);

// Protected methods (used internally by page objects)
protected void navigateTo(String url);
protected void click(String selector);
protected void fill(String selector, String text);
protected void selectOption(String selector, String value);
protected void check(String selector);
protected void uncheck(String selector);
protected String getText(String selector);
protected boolean isVisible(String selector);
protected void waitForElement(String selector);
protected void waitForPageLoad();

// Public methods
public String getPageTitle();
public String getCurrentUrl();
public boolean isErrorMessageDisplayed(String errorText);
public String getErrorMessage(String selector);
```

### HomePage
```java
public HomePage(Page page);

public HomePage navigate();                          // navigates to baseUrl, returns this
public CustomerDetailsPage clickGetQuote();          // → CustomerDetailsPage
public CustomerDetailsPage clickCreatePolicy();      // → CustomerDetailsPage (alternative entry)
public boolean isHomePageDisplayed();                // checks logo + get quote button
```

### CustomerDetailsPage
```java
public CustomerDetailsPage(Page page);

// Bulk fill
public CustomerDetailsPage fillCustomerDetails(Customer customer);  // fills all fields, returns this

// Individual field methods (all return this for chaining)
public CustomerDetailsPage fillTitle(String title);
public CustomerDetailsPage fillFirstName(String firstName);
public CustomerDetailsPage fillLastName(String lastName);
public CustomerDetailsPage fillEmail(String email);
public CustomerDetailsPage fillPostcode(String postcode);

// Navigation
public VehicleDetailsPage clickNext();               // → VehicleDetailsPage

// Verification
public boolean isCustomerDetailsPageDisplayed();     // checks firstName + lastName inputs
public String getValidationError();                  // gets validation error text
public boolean isValidationErrorDisplayed();         // checks if validation error visible
```

### VehicleDetailsPage
```java
public VehicleDetailsPage(Page page);

// Vehicle operations
public VehicleDetailsPage lookupVehicle(String registrationNumber);  // fill reg + click lookup
public VehicleDetailsPage fillVehicleDetails(Vehicle vehicle);       // fills all fields, returns this
public VehicleDetailsPage fillRegistration(String registration);     // fill reg only, returns this

// Data retrieval
public boolean isVehicleFound();                     // checks vehicle-found-message
public String getVehicleMake();                      // gets make input value
public String getVehicleModel();                     // gets model input value

// Navigation
public CoverSelectionPage clickNext();               // → CoverSelectionPage
public CustomerDetailsPage clickBack();              // → CustomerDetailsPage

// Verification
public boolean isVehicleDetailsPageDisplayed();      // checks registration + lookup
public String getValidationError();
public boolean isInvalidRegistrationErrorDisplayed(); // checks "Invalid registration number"
```

### CoverSelectionPage
```java
public CoverSelectionPage(Page page);

// Cover type selection
public CoverSelectionPage selectCoverType(Policy.CoverType coverType);  // returns this

// Start date
public CoverSelectionPage setStartDate(LocalDate startDate);            // returns this

// Add-ons
public CoverSelectionPage selectAddOns(List<Policy.AddOn> addOns);      // returns this
public CoverSelectionPage selectAddOn(Policy.AddOn addOn);              // returns this
public CoverSelectionPage deselectAddOn(Policy.AddOn addOn);            // returns this

// Premium
public CoverSelectionPage calculatePremium();        // clicks calculate, waits for display
public String getPremiumAmount();                    // raw text
public String getTotalPremiumAmount();               // raw text including add-ons
public double getPremiumValue();                     // parsed numeric value
public double getTotalPremiumValue();                // parsed numeric total

// Navigation
public PolicyReviewPage clickNext();                 // → PolicyReviewPage
public VehicleDetailsPage clickBack();               // → VehicleDetailsPage

// Verification
public boolean isCoverSelectionPageDisplayed();      // checks radio + start date
public boolean isPastDateErrorDisplayed();           // checks past date error message
public String getValidationError();
```

### PolicyReviewPage
```java
public PolicyReviewPage(Page page);

// Data retrieval (review displayed data)
public String getCustomerName();
public String getCustomerEmail();
public String getVehicleDetails();
public String getCoverType();
public String getStartDate();
public String getPremium();
public String getAddOns();
public String getTotalPremium();

// Actions
public PolicyReviewPage acceptTerms();                      // ⚠️ MUST call before confirmPolicy()
public PolicyConfirmationPage confirmPolicy();              // ⚠️ NOT "clickConfirmPolicy()"
public CoverSelectionPage editPolicy();                     // → CoverSelectionPage
public CoverSelectionPage clickBack();                      // → CoverSelectionPage

// Verification
public boolean isPolicyReviewPageDisplayed();               // checks name display + confirm button
public boolean areAllDetailsDisplayed();                    // checks all review fields
```

### PolicyConfirmationPage
```java
public PolicyConfirmationPage(Page page);

// Verification
public boolean isPolicyCreatedSuccessfully();        // ⚠️ NOT "isConfirmationDisplayed()"
public boolean isConfirmationPageDisplayed();        // checks title + policy number
public boolean isPolicyActive();                     // checks status == "Active"

// Data retrieval
public String getPolicyNumber();                     // gets policy number text
public String getPolicyStatus();                     // gets status text
public String getSuccessMessage();                   // gets success message text
public String extractPolicyNumber();                 // extracts alphanumeric policy number

// Actions
public void downloadPolicy();
public void viewPolicy();
public void goHome();
```

---

## ⚠️ COMMON MISTAKES TO AVOID

| ❌ Wrong (does NOT exist) | ✅ Correct (actual method) |
|---|---|
| `policyReviewPage.clickConfirmPolicy()` | `policyReviewPage.confirmPolicy()` |
| `confirmationPage.isConfirmationDisplayed()` | `confirmationPage.isPolicyCreatedSuccessfully()` |
| `new HomePage(this.page)` | `new HomePage(page)` |
| Skipping `acceptTerms()` before confirm | `reviewPage.acceptTerms().confirmPolicy()` |
| Skipping `calculatePremium()` | Call before `clickNext()` on CoverSelectionPage |
| Skipping `setStartDate()` | Always set start date on CoverSelectionPage |
| `customerDetailsPage.clickNextExpectingError()` | This method does NOT exist — use `clickNext()` or check validation after action |

---

## 📊 TEST DATA BUILDER (Exact methods from source)

```java
// Valid data
Customer customer = TestDataBuilder.createValidCustomer();
Customer customer = TestDataBuilder.createCustomer("John", "Doe", "john@test.com");
Vehicle vehicle = TestDataBuilder.createValidVehicle();

// Invalid data for negative tests
Vehicle invalidVehicle = TestDataBuilder.createVehicleWithInvalidRegistration();

// Policy builders
Policy policy = TestDataBuilder.createValidPolicyWithComprehensiveCover();
Policy policy = TestDataBuilder.createPolicyWithTPFTCover();
Policy policy = TestDataBuilder.createPolicyWithTPOCover();
Policy policy = TestDataBuilder.createPolicyWithAddOns();          // Breakdown + Legal
Policy policy = TestDataBuilder.createPolicyWithPastStartDate();   // For negative tests

// Utility
String policyNumber = TestDataBuilder.generatePolicyNumber();      // "ESR" + timestamp
```

---

## ✅ TEST CLASS PATTERNS

### Test Class Structure
```java
package com.esure.insurance.tests;

import com.esure.insurance.base.BaseTest;
import com.esure.insurance.models.Customer;
import com.esure.insurance.models.Policy;
import com.esure.insurance.models.Vehicle;
import com.esure.insurance.pages.*;
import com.esure.insurance.utils.TestDataBuilder;
import org.testng.annotations.Test;
import java.time.LocalDate;
import java.util.*;
import static org.assertj.core.api.Assertions.assertThat;

// ✅ MUST extend BaseTest — provides: protected Page page;
public class <Feature>Tests extends BaseTest {

    @Test(priority = 1, description = "Test description here")
    public void test<ScenarioName>() {
        // Arrange
        Customer customer = TestDataBuilder.createValidCustomer();
        Vehicle vehicle = TestDataBuilder.createValidVehicle();

        // Act
        HomePage homePage = new HomePage(page);
        CustomerDetailsPage customerDetailsPage = homePage.navigate().clickGetQuote();
        // ... (see full flow example below)

        // Assert
        assertThat(result).as("Description").isTrue();
    }
}
```

### Full Happy-Path Flow (verified against PolicyCreationTests.java)
```java
@Test(priority = 1, description = "Create policy with valid data")
public void testCreatePolicyWithValidData() {
    // Arrange
    Customer customer = TestDataBuilder.createValidCustomer();
    Vehicle vehicle = TestDataBuilder.createValidVehicle();

    // Act - Step 1: Navigate and start quote
    HomePage homePage = new HomePage(page);
    CustomerDetailsPage customerDetailsPage = homePage.navigate().clickGetQuote();
    assertThat(customerDetailsPage.isCustomerDetailsPageDisplayed())
            .as("Customer details page should be displayed").isTrue();

    // Act - Step 2: Fill customer details and proceed
    VehicleDetailsPage vehicleDetailsPage = customerDetailsPage
            .fillCustomerDetails(customer)
            .clickNext();
    assertThat(vehicleDetailsPage.isVehicleDetailsPageDisplayed())
            .as("Vehicle details page should be displayed").isTrue();

    // Act - Step 3: Fill vehicle details and proceed
    CoverSelectionPage coverSelectionPage = vehicleDetailsPage
            .fillVehicleDetails(vehicle)
            .clickNext();
    assertThat(coverSelectionPage.isCoverSelectionPageDisplayed())
            .as("Cover selection page should be displayed").isTrue();

    // Act - Step 4: Select cover, set date, calculate premium, proceed
    PolicyReviewPage reviewPage = coverSelectionPage
            .selectCoverType(Policy.CoverType.COMPREHENSIVE)
            .setStartDate(LocalDate.now().plusDays(1))
            .calculatePremium()
            .clickNext();
    assertThat(reviewPage.isPolicyReviewPageDisplayed())
            .as("Policy review page should be displayed").isTrue();

    // Act - Step 5: Accept terms and confirm (BOTH steps required)
    PolicyConfirmationPage confirmationPage = reviewPage
            .acceptTerms()
            .confirmPolicy();

    // Assert
    assertThat(confirmationPage.isPolicyCreatedSuccessfully())
            .as("Policy should be created successfully").isTrue();

    String policyNumber = confirmationPage.getPolicyNumber();
    assertThat(policyNumber)
            .as("Policy number should be generated")
            .isNotNull().isNotEmpty();

    assertThat(confirmationPage.isPolicyActive())
            .as("Policy status should be Active").isTrue();

    System.out.println("Policy created successfully with number: " + policyNumber);
}
```

### AssertJ Assertion Patterns
```java
// Boolean
assertThat(confirmationPage.isPolicyCreatedSuccessfully())
        .as("Policy should be created successfully").isTrue();

// String
assertThat(reviewPage.getCustomerName())
        .as("Customer name should match").contains(customer.getFirstName());
assertThat(policyNumber).as("Policy number generated").isNotNull().isNotEmpty();

// Numeric
assertThat(totalPremium).as("Premium includes add-ons").isGreaterThan(basePremium);

// Page verification
assertThat(customerDetailsPage.isCustomerDetailsPageDisplayed())
        .as("Customer details page should be displayed").isTrue();
```

---

## 📥 INPUT FORMAT: MANUAL TEST CASE

When you receive a manual test case, it will be in this format:

```
TEST CASE ID: TC_XXX
TEST CASE TITLE: <Title>
PRIORITY: High/Medium/Low
PRECONDITIONS:
- <Precondition 1>

TEST STEPS:
1. <Step 1>
2. <Step 2>

TEST DATA:
- Field1: Value1

EXPECTED RESULTS:
- <Expected outcome 1>

ACCEPTANCE CRITERIA:
- <AC 1>
```

---

## 📤 OUTPUT FORMAT: AUTOMATION SCRIPT

### 1. Test Method
```java
/**
 * Test Scenario: <Description>
 * Test Case ID: TC_XXX
 */
@Test(priority = <N>, description = "<Test case title>")
public void test<ScenarioName>() {
    // Arrange
    <test data setup using TestDataBuilder>

    // Act
    <test steps using ONLY methods listed in the API reference above>

    // Assert
    <assertions using ONLY verification methods listed above>

    System.out.println("<Success message>");
}
```

### 2. New Page Object Methods (if needed — mark clearly)
```java
// ⚠️ NEW METHOD — does not exist yet, must be added to <PageName>.java
public <ReturnType> <methodName>(<parameters>) {
    <implementation>
}
```

---

## 🎨 CODE STYLE GUIDELINES

### Naming Conventions
- **Test Methods**: `test<WhatIsBeingTested>` (camelCase)
- **Page Methods**: `<action><Element>` (e.g., `fillFirstName`, `clickNext`)
- **Locators**: `<ELEMENT_NAME>_<TYPE>` (UPPER_SNAKE_CASE)
- **Variables**: camelCase
- **Constants**: UPPER_SNAKE_CASE

### Method Chaining
Page object methods return `this` for fluent chaining. Navigation methods return the next page:
```java
// Correct chaining pattern
VehicleDetailsPage vehicleDetailsPage = customerDetailsPage
        .fillCustomerDetails(customer)   // returns CustomerDetailsPage (this)
        .clickNext();                    // returns VehicleDetailsPage (new page)
```

### Assertions
- Always include `.as("description")` for meaningful failure messages
- Verify page state after navigation before interacting

---

## ⚠️ IMPORTANT RULES

1. **🔴 ALWAYS extend BaseTest** — `public class <ClassName> extends BaseTest`
2. **🔴 ONLY use methods that exist** in the API reference above
3. **🔴 ALWAYS call `acceptTerms()` before `confirmPolicy()`** on PolicyReviewPage
4. **🔴 ALWAYS call `setStartDate()` and `calculatePremium()`** on CoverSelectionPage before proceeding
5. **Always use Page Object pattern** — no direct `page.locator()` in tests
6. **Always use TestDataBuilder** for test data
7. **Always use AssertJ** with `.as("description")`
8. **Always follow Arrange-Act-Assert**
9. **Use `page` not `this.page`** when constructing page objects
10. **Keep tests independent** — no test depends on another
11. **Include priority** in `@Test` annotation

---

## 🔄 READY FOR INPUT

Provide your manual test case(s) and I will generate automation scripts using **only verified methods from the codebase**.
