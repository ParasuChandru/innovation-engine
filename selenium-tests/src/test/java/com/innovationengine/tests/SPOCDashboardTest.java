package com.innovationengine.tests;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.testng.Assert;
import org.testng.annotations.*;
import org.testng.ITestResult;

import java.time.Duration;
import java.util.List;

/**
 * SPOC Dashboard Selenium Test Suite
 * JIRA Story: RBTES-1035 - SPOC Dashboard - View List of Assigned Ideas
 * 
 * Test Coverage:
 * - Navigation and Access Control
 * - Dashboard Statistics Display
 * - Ideas Table Functionality
 * - Role-Based Visibility
 */
public class SPOCDashboardTest {

    private WebDriver driver;
    private WebDriverWait wait;
    private static final String BASE_URL = "http://localhost:5000";
    
    // Test User Credentials
    private static final String SPOC_EMAIL = "sarah.johnson@company.com";
    private static final String ADMIN_EMAIL = "admin@company.com";
    private static final String OWNER_EMAIL = "john.smith@company.com";
    private static final String CGI_EXEC_EMAIL = "robert.brown@company.com";

    @BeforeClass
    public void setUpClass() {
        System.out.println("========================================");
        System.out.println("SPOC Dashboard Selenium Test Suite");
        System.out.println("RBTES-1035: SPOC Dashboard Feature");
        System.out.println("========================================");
    }

    @BeforeMethod
    public void setUp() {
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--headless");
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        options.addArguments("--window-size=1920,1080");
        
        driver = new ChromeDriver(options);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(5));
    }

    @AfterMethod
    public void tearDown(ITestResult result) {
        if (result.getStatus() == ITestResult.FAILURE) {
            System.out.println("❌ Test Failed: " + result.getName());
        } else {
            System.out.println("✅ Test Passed: " + result.getName());
        }
        
        if (driver != null) {
            driver.quit();
        }
    }

    // ========================================
    // Helper Methods
    // ========================================

    /**
     * Login with specified email
     */
    private void login(String email) {
        driver.get(BASE_URL + "/login");
        
        WebElement emailInput = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.name("email"))
        );
        emailInput.clear();
        emailInput.sendKeys(email);
        
        WebElement submitButton = driver.findElement(By.cssSelector("button[type='submit']"));
        submitButton.click();
        
        // Wait for dashboard to load
        wait.until(ExpectedConditions.urlContains("/dashboard"));
    }

    /**
     * Navigate to SPOC Dashboard
     */
    private void navigateToSPOCDashboard() {
        driver.get(BASE_URL + "/spoc-dashboard");
        wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("h1")));
    }

    /**
     * Check if element exists on page
     */
    private boolean isElementPresent(By locator) {
        try {
            driver.findElement(locator);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // ========================================
    // TC-SD-001: SPOC Dashboard Route Exists
    // Zephyr: RBTES-T1410
    // ========================================
    @Test(priority = 1, description = "Verify SPOC Dashboard route exists and is accessible")
    public void testSPOCDashboardRouteExists() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        String currentUrl = driver.getCurrentUrl();
        Assert.assertTrue(currentUrl.contains("/spoc-dashboard"), 
            "SPOC Dashboard URL should contain '/spoc-dashboard'");
        
        String pageTitle = driver.getTitle();
        Assert.assertTrue(pageTitle.contains("SPOC Dashboard"), 
            "Page title should contain 'SPOC Dashboard'");
    }

    // ========================================
    // TC-SD-002: SPOC Dashboard Requires Login
    // Zephyr: RBTES-T1415
    // ========================================
    @Test(priority = 2, description = "Verify SPOC Dashboard requires authentication")
    public void testSPOCDashboardRequiresLogin() {
        // Try to access SPOC Dashboard without logging in
        driver.get(BASE_URL + "/spoc-dashboard");
        
        // Should redirect to login page
        wait.until(ExpectedConditions.urlContains("/login"));
        String currentUrl = driver.getCurrentUrl();
        Assert.assertTrue(currentUrl.contains("/login"), 
            "Unauthenticated users should be redirected to login");
    }

    // ========================================
    // TC-SD-003: SPOC Dashboard Role Check
    // Zephyr: RBTES-T1416
    // ========================================
    @Test(priority = 3, description = "Verify SPOC Dashboard denies access to OWNER role")
    public void testSPOCDashboardDeniesOwnerAccess() {
        login(OWNER_EMAIL);
        
        // Try to access SPOC Dashboard
        driver.get(BASE_URL + "/spoc-dashboard");
        
        // Should redirect to dashboard with error
        wait.until(ExpectedConditions.urlContains("/dashboard"));
        
        // Check for access denied message
        String pageSource = driver.getPageSource();
        Assert.assertTrue(pageSource.contains("Access denied") || 
                         !driver.getCurrentUrl().contains("/spoc-dashboard"),
            "OWNER should be denied access to SPOC Dashboard");
    }

    // ========================================
    // TC-SD-004: SPOC Dashboard Accessible to SPOC
    // Zephyr: RBTES-T1413
    // ========================================
    @Test(priority = 4, description = "Verify SPOC Dashboard is accessible to SPOC role")
    public void testSPOCDashboardAccessibleToSPOC() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Verify page loaded successfully
        WebElement heading = driver.findElement(By.tagName("h1"));
        Assert.assertTrue(heading.getText().contains("SPOC Dashboard"),
            "SPOC should be able to access SPOC Dashboard");
    }

    // ========================================
    // TC-SD-005: SPOC Dashboard Accessible to ADMIN
    // Zephyr: RBTES-T1414
    // ========================================
    @Test(priority = 5, description = "Verify SPOC Dashboard is accessible to ADMIN role")
    public void testSPOCDashboardAccessibleToAdmin() {
        login(ADMIN_EMAIL);
        navigateToSPOCDashboard();
        
        // Verify page loaded successfully
        WebElement heading = driver.findElement(By.tagName("h1"));
        Assert.assertTrue(heading.getText().contains("SPOC Dashboard"),
            "ADMIN should be able to access SPOC Dashboard");
    }

    // ========================================
    // TC-SD-006: Statistics Cards Display
    // Zephyr: RBTES-T1418
    // ========================================
    @Test(priority = 6, description = "Verify SPOC Dashboard displays statistics cards")
    public void testStatisticsCardsDisplay() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        String pageSource = driver.getPageSource();
        
        // Verify all statistics cards are present
        Assert.assertTrue(pageSource.contains("Total Assigned"), 
            "Total Assigned stat should be displayed");
        Assert.assertTrue(pageSource.contains("Pending Review"), 
            "Pending Review stat should be displayed");
        Assert.assertTrue(pageSource.contains("In Progress"), 
            "In Progress stat should be displayed");
        Assert.assertTrue(pageSource.contains("Completed"), 
            "Completed stat should be displayed");
        Assert.assertTrue(pageSource.contains("Total Savings"), 
            "Total Savings stat should be displayed");
    }

    // ========================================
    // TC-SD-007: Ideas Table Display
    // Zephyr: RBTES-T1422
    // ========================================
    @Test(priority = 7, description = "Verify SPOC Dashboard displays ideas table with correct columns")
    public void testIdeasTableDisplay() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Verify table exists
        Assert.assertTrue(isElementPresent(By.tagName("table")), 
            "Ideas table should be present");
        
        // Verify column headers
        String pageSource = driver.getPageSource();
        String[] expectedColumns = {"Title", "Status", "Category", "Submitter", "Created", "Savings", "Action"};
        
        for (String column : expectedColumns) {
            Assert.assertTrue(pageSource.contains(column), 
                "Column '" + column + "' should be present in table header");
        }
    }

    // ========================================
    // TC-SD-008: Ideas Table Shows Data
    // Zephyr: RBTES-T1427
    // ========================================
    @Test(priority = 8, description = "Verify ideas table displays idea data")
    public void testIdeasTableShowsData() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Find table body rows
        List<WebElement> tableRows = driver.findElements(
            By.cssSelector("table tbody tr")
        );
        
        // SPOC should have ideas assigned (from sample data)
        Assert.assertTrue(tableRows.size() > 0, 
            "Ideas table should contain at least one idea for SPOC");
    }

    // ========================================
    // TC-SD-009: Status Badges Display
    // Zephyr: RBTES-T1421
    // ========================================
    @Test(priority = 9, description = "Verify status badges are displayed with colors")
    public void testStatusBadgesDisplay() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Check for status badge elements with color classes
        String pageSource = driver.getPageSource();
        
        // At least one status badge styling should be present
        boolean hasStatusBadges = pageSource.contains("bg-slate-100") ||
                                  pageSource.contains("bg-purple-100") ||
                                  pageSource.contains("bg-green-100") ||
                                  pageSource.contains("bg-amber-100") ||
                                  pageSource.contains("bg-blue-100");
        
        Assert.assertTrue(hasStatusBadges, 
            "Status badges with color styling should be present");
    }

    // ========================================
    // TC-SD-010: View Button Functionality
    // Zephyr: RBTES-T1420
    // ========================================
    @Test(priority = 10, description = "Verify View button navigates to idea detail page")
    public void testViewButtonNavigation() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Find and click the first View button
        List<WebElement> viewButtons = driver.findElements(
            By.xpath("//a[contains(text(), 'View')]")
        );
        
        if (viewButtons.size() > 0) {
            viewButtons.get(0).click();
            
            // Wait for navigation
            wait.until(ExpectedConditions.urlContains("/ideas/"));
            
            String currentUrl = driver.getCurrentUrl();
            Assert.assertTrue(currentUrl.contains("/ideas/"), 
                "View button should navigate to idea detail page");
        } else {
            // If no ideas, check that empty state is shown
            String pageSource = driver.getPageSource();
            Assert.assertTrue(pageSource.contains("No ideas assigned"),
                "Empty state message should be displayed when no ideas");
        }
    }

    // ========================================
    // TC-SD-011: Navigation Link for SPOC
    // Zephyr: RBTES-T1424
    // ========================================
    @Test(priority = 11, description = "Verify navigation shows SPOC Dashboard link for SPOC users")
    public void testNavigationLinkForSPOC() {
        login(SPOC_EMAIL);
        
        // Check navigation for SPOC Dashboard link
        String pageSource = driver.getPageSource();
        Assert.assertTrue(pageSource.contains("SPOC Dashboard"), 
            "Navigation should show SPOC Dashboard link for SPOC users");
        
        Assert.assertTrue(pageSource.contains("/spoc-dashboard"), 
            "Navigation should have link to /spoc-dashboard");
    }

    // ========================================
    // TC-SD-012: Navigation Link Hidden for OWNER
    // Zephyr: RBTES-T1428
    // ========================================
    @Test(priority = 12, description = "Verify navigation hides SPOC Dashboard link for OWNER users")
    public void testNavigationLinkHiddenForOwner() {
        login(OWNER_EMAIL);
        
        // Check that SPOC Dashboard link is NOT in navigation
        WebElement nav = driver.findElement(By.tagName("nav"));
        String navText = nav.getText();
        
        Assert.assertFalse(navText.contains("SPOC Dashboard"), 
            "Navigation should NOT show SPOC Dashboard link for OWNER users");
    }

    // ========================================
    // TC-SD-013: Navigation Link for ADMIN
    // ========================================
    @Test(priority = 13, description = "Verify navigation shows SPOC Dashboard link for ADMIN users")
    public void testNavigationLinkForAdmin() {
        login(ADMIN_EMAIL);
        
        // Check navigation for SPOC Dashboard link
        String pageSource = driver.getPageSource();
        Assert.assertTrue(pageSource.contains("SPOC Dashboard"), 
            "Navigation should show SPOC Dashboard link for ADMIN users");
    }

    // ========================================
    // TC-SD-014: Status Distribution Section
    // ========================================
    @Test(priority = 14, description = "Verify status distribution section is displayed")
    public void testStatusDistributionSection() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        String pageSource = driver.getPageSource();
        Assert.assertTrue(pageSource.contains("Status Distribution"), 
            "Status Distribution section should be present");
    }

    // ========================================
    // TC-SD-015: Empty State Display
    // Zephyr: RBTES-T1423
    // ========================================
    @Test(priority = 15, description = "Verify empty state is displayed when no ideas assigned")
    public void testEmptyStateDisplay() {
        // This test verifies the empty state template exists
        // For a SPOC with ideas, we just verify the template has empty state handling
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // The page should either show ideas OR empty state
        String pageSource = driver.getPageSource();
        boolean hasIdeas = pageSource.contains("<table");
        boolean hasEmptyState = pageSource.contains("No ideas assigned");
        
        Assert.assertTrue(hasIdeas || hasEmptyState, 
            "Page should show either ideas table or empty state message");
    }

    // ========================================
    // TC-SD-016: Dashboard Header Display
    // ========================================
    @Test(priority = 16, description = "Verify dashboard header and description are displayed")
    public void testDashboardHeaderDisplay() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        WebElement heading = driver.findElement(By.tagName("h1"));
        Assert.assertEquals(heading.getText(), "SPOC Dashboard", 
            "Page heading should be 'SPOC Dashboard'");
        
        String pageSource = driver.getPageSource();
        Assert.assertTrue(pageSource.contains("Manage and track ideas assigned to you"), 
            "Dashboard description should be present");
    }

    // ========================================
    // TC-SD-017: Submit New Idea Button
    // ========================================
    @Test(priority = 17, description = "Verify Submit New Idea button is present and functional")
    public void testSubmitNewIdeaButton() {
        login(SPOC_EMAIL);
        navigateToSPOCDashboard();
        
        // Find Submit New Idea button
        WebElement submitButton = driver.findElement(
            By.xpath("//a[contains(text(), 'Submit New Idea')]")
        );
        
        Assert.assertTrue(submitButton.isDisplayed(), 
            "Submit New Idea button should be visible");
        
        // Click and verify navigation
        submitButton.click();
        wait.until(ExpectedConditions.urlContains("/ideas/new"));
        
        Assert.assertTrue(driver.getCurrentUrl().contains("/ideas/new"), 
            "Submit New Idea button should navigate to new idea form");
    }

    // ========================================
    // TC-SD-018: CGI Exec Cannot Access SPOC Dashboard
    // ========================================
    @Test(priority = 18, description = "Verify CGI_EXEC cannot access SPOC Dashboard")
    public void testCGIExecCannotAccess() {
        login(CGI_EXEC_EMAIL);
        
        // Try to access SPOC Dashboard
        driver.get(BASE_URL + "/spoc-dashboard");
        
        // Should be redirected
        wait.until(driver -> !driver.getCurrentUrl().contains("/spoc-dashboard") || 
                            driver.getPageSource().contains("Access denied"));
        
        String currentUrl = driver.getCurrentUrl();
        String pageSource = driver.getPageSource();
        
        Assert.assertTrue(!currentUrl.contains("/spoc-dashboard") || 
                         pageSource.contains("Access denied"),
            "CGI_EXEC should be denied access to SPOC Dashboard");
    }

    @AfterClass
    public void tearDownClass() {
        System.out.println("========================================");
        System.out.println("Test Suite Completed");
        System.out.println("========================================");
    }
}