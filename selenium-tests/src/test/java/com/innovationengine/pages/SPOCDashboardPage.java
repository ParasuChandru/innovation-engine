package com.innovationengine.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Page Object Model for SPOC Dashboard Page
 * Innovation Engine Application
 * JIRA Story: RBTES-1035
 */
public class SPOCDashboardPage {
    
    private WebDriver driver;
    private WebDriverWait wait;
    private static final String PAGE_URL = "/spoc-dashboard";
    
    // Page Elements - Header
    @FindBy(tagName = "h1")
    private WebElement pageHeading;
    
    @FindBy(xpath = "//p[contains(@class, 'text-gray-500')]")
    private WebElement pageDescription;
    
    @FindBy(xpath = "//a[contains(text(), 'Submit New Idea')]")
    private WebElement submitNewIdeaButton;
    
    // Statistics Cards
    @FindBy(xpath = "//span[contains(text(), 'Total Assigned')]/parent::div/following-sibling::div")
    private WebElement totalAssignedStat;
    
    @FindBy(xpath = "//span[contains(text(), 'Pending Review')]/parent::div/following-sibling::div")
    private WebElement pendingReviewStat;
    
    @FindBy(xpath = "//span[contains(text(), 'In Progress')]/parent::div/following-sibling::div")
    private WebElement inProgressStat;
    
    @FindBy(xpath = "//span[contains(text(), 'Completed')]/parent::div/following-sibling::div")
    private WebElement completedStat;
    
    @FindBy(xpath = "//span[contains(text(), 'Total Savings')]/parent::div/following-sibling::div")
    private WebElement totalSavingsStat;
    
    // Status Distribution Section
    @FindBy(xpath = "//h2[contains(text(), 'Status Distribution')]")
    private WebElement statusDistributionHeading;
    
    @FindBy(css = ".rounded-full")
    private List<WebElement> statusBadges;
    
    // Ideas Table
    @FindBy(css = "table")
    private WebElement ideasTable;
    
    @FindBy(css = "table thead th")
    private List<WebElement> tableHeaders;
    
    @FindBy(css = "table tbody tr")
    private List<WebElement> ideaRows;
    
    @FindBy(xpath = "//a[contains(text(), 'View')]")
    private List<WebElement> viewButtons;
    
    // Empty State
    @FindBy(xpath = "//h3[contains(text(), 'No ideas assigned')]")
    private WebElement emptyStateHeading;
    
    @FindBy(xpath = "//p[contains(text(), 'Ideas will appear here')]")
    private WebElement emptyStateMessage;
    
    // Flash Messages
    @FindBy(css = ".bg-red-50")
    private WebElement errorMessage;
    
    @FindBy(css = ".bg-green-50")
    private WebElement successMessage;
    
    /**
     * Constructor
     */
    public SPOCDashboardPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        PageFactory.initElements(driver, this);
    }
    
    /**
     * Navigate to SPOC Dashboard
     */
    public SPOCDashboardPage navigateTo(String baseUrl) {
        driver.get(baseUrl + PAGE_URL);
        wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("h1")));
        return this;
    }
    
    /**
     * Check if on SPOC Dashboard page
     */
    public boolean isOnSPOCDashboardPage() {
        return driver.getCurrentUrl().contains("/spoc-dashboard");
    }
    
    // Header Methods
    
    public String getPageHeading() {
        wait.until(ExpectedConditions.visibilityOf(pageHeading));
        return pageHeading.getText();
    }
    
    public String getPageDescription() {
        return pageDescription.getText();
    }
    
    public void clickSubmitNewIdea() {
        wait.until(ExpectedConditions.elementToBeClickable(submitNewIdeaButton));
        submitNewIdeaButton.click();
        wait.until(ExpectedConditions.urlContains("/ideas/new"));
    }
    
    public boolean isSubmitNewIdeaButtonVisible() {
        try {
            return submitNewIdeaButton.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    // Statistics Methods
    
    public String getTotalAssigned() {
        return totalAssignedStat.getText();
    }
    
    public String getPendingReview() {
        return pendingReviewStat.getText();
    }
    
    public String getInProgress() {
        return inProgressStat.getText();
    }
    
    public String getCompleted() {
        return completedStat.getText();
    }
    
    public String getTotalSavings() {
        return totalSavingsStat.getText();
    }
    
    public boolean areAllStatisticsDisplayed() {
        try {
            return totalAssignedStat.isDisplayed() &&
                   pendingReviewStat.isDisplayed() &&
                   inProgressStat.isDisplayed() &&
                   completedStat.isDisplayed() &&
                   totalSavingsStat.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    // Status Distribution Methods
    
    public boolean isStatusDistributionVisible() {
        try {
            return statusDistributionHeading.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    public int getStatusBadgesCount() {
        return statusBadges.size();
    }
    
    // Ideas Table Methods
    
    public boolean isIdeasTableDisplayed() {
        try {
            return ideasTable.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    public List<String> getTableHeaders() {
        return tableHeaders.stream()
            .map(WebElement::getText)
            .collect(Collectors.toList());
    }
    
    public int getIdeasCount() {
        return ideaRows.size();
    }
    
    public String getIdeaTitleAt(int index) {
        if (index < ideaRows.size()) {
            WebElement row = ideaRows.get(index);
            WebElement titleCell = row.findElement(By.cssSelector("td:first-child a"));
            return titleCell.getText();
        }
        return "";
    }
    
    public String getIdeaStatusAt(int index) {
        if (index < ideaRows.size()) {
            WebElement row = ideaRows.get(index);
            WebElement statusBadge = row.findElement(By.cssSelector("td:nth-child(2) span"));
            return statusBadge.getText();
        }
        return "";
    }
    
    public IdeaDetailPage clickViewButtonAt(int index) {
        if (index < viewButtons.size()) {
            viewButtons.get(index).click();
            wait.until(ExpectedConditions.urlContains("/ideas/"));
            return new IdeaDetailPage(driver);
        }
        return null;
    }
    
    public boolean areViewButtonsPresent() {
        return viewButtons.size() > 0;
    }
    
    // Empty State Methods
    
    public boolean isEmptyStateDisplayed() {
        try {
            return emptyStateHeading.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    public String getEmptyStateMessage() {
        try {
            return emptyStateMessage.getText();
        } catch (Exception e) {
            return "";
        }
    }
    
    // Flash Message Methods
    
    public boolean isErrorMessageDisplayed() {
        try {
            return errorMessage.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    public String getErrorMessage() {
        try {
            return errorMessage.getText();
        } catch (Exception e) {
            return "";
        }
    }
    
    // Utility Methods
    
    public String getPageSource() {
        return driver.getPageSource();
    }
    
    public String getCurrentUrl() {
        return driver.getCurrentUrl();
    }
    
    public SPOCDashboardPage refresh() {
        driver.navigate().refresh();
        wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("h1")));
        return this;
    }
}