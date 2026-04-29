package com.innovationengine.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

/**
 * Page Object Model for Dashboard Page
 * Innovation Engine Application
 */
public class DashboardPage {
    
    private WebDriver driver;
    private WebDriverWait wait;
    
    // Navigation Elements
    @FindBy(xpath = "//a[contains(@href, '/spoc-dashboard')]")
    private WebElement spocDashboardLink;
    
    @FindBy(xpath = "//a[contains(@href, '/dashboard')]")
    private WebElement dashboardLink;
    
    @FindBy(xpath = "//a[contains(@href, '/kanban')]")
    private WebElement kanbanLink;
    
    @FindBy(xpath = "//a[contains(@href, '/ideas/new')]")
    private WebElement submitIdeaLink;
    
    @FindBy(xpath = "//a[contains(@href, '/logout')]")
    private WebElement logoutLink;
    
    // Page Elements
    @FindBy(css = "h1")
    private WebElement pageHeading;
    
    @FindBy(css = "nav")
    private WebElement navigation;
    
    /**
     * Constructor
     */
    public DashboardPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        PageFactory.initElements(driver, this);
    }
    
    /**
     * Navigate to SPOC Dashboard
     */
    public SPOCDashboardPage goToSPOCDashboard() {
        wait.until(ExpectedConditions.elementToBeClickable(spocDashboardLink));
        spocDashboardLink.click();
        wait.until(ExpectedConditions.urlContains("/spoc-dashboard"));
        return new SPOCDashboardPage(driver);
    }
    
    /**
     * Check if SPOC Dashboard link is visible in navigation
     */
    public boolean isSPOCDashboardLinkVisible() {
        try {
            return spocDashboardLink.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Get navigation text
     */
    public String getNavigationText() {
        return navigation.getText();
    }
    
    /**
     * Get page heading
     */
    public String getPageHeading() {
        return pageHeading.getText();
    }
    
    /**
     * Navigate to Submit Idea page
     */
    public void goToSubmitIdea() {
        submitIdeaLink.click();
        wait.until(ExpectedConditions.urlContains("/ideas/new"));
    }
    
    /**
     * Logout
     */
    public LoginPage logout() {
        logoutLink.click();
        wait.until(ExpectedConditions.urlContains("/login"));
        return new LoginPage(driver);
    }
    
    /**
     * Check if on dashboard page
     */
    public boolean isOnDashboardPage() {
        return driver.getCurrentUrl().contains("/dashboard");
    }
}