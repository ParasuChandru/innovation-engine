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
 * Page Object Model for Login Page
 * Innovation Engine Application
 */
public class LoginPage {
    
    private WebDriver driver;
    private WebDriverWait wait;
    private static final String PAGE_URL = "/login";
    
    // Page Elements
    @FindBy(name = "email")
    private WebElement emailInput;
    
    @FindBy(css = "button[type='submit']")
    private WebElement loginButton;
    
    @FindBy(css = ".bg-red-50")
    private WebElement errorMessage;
    
    @FindBy(css = "h1")
    private WebElement pageTitle;
    
    // Demo account quick login buttons
    @FindBy(xpath = "//button[contains(text(), 'admin@company.com')]")
    private WebElement adminQuickLogin;
    
    @FindBy(xpath = "//button[contains(text(), 'sarah.johnson@company.com')]")
    private WebElement spocQuickLogin;
    
    /**
     * Constructor
     */
    public LoginPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        PageFactory.initElements(driver, this);
    }
    
    /**
     * Navigate to login page
     */
    public LoginPage navigateTo(String baseUrl) {
        driver.get(baseUrl + PAGE_URL);
        wait.until(ExpectedConditions.presenceOfElementLocated(By.name("email")));
        return this;
    }
    
    /**
     * Enter email address
     */
    public LoginPage enterEmail(String email) {
        wait.until(ExpectedConditions.visibilityOf(emailInput));
        emailInput.clear();
        emailInput.sendKeys(email);
        return this;
    }
    
    /**
     * Click login button
     */
    public void clickLogin() {
        loginButton.click();
    }
    
    /**
     * Perform login with email
     */
    public DashboardPage login(String email) {
        enterEmail(email);
        clickLogin();
        wait.until(ExpectedConditions.urlContains("/dashboard"));
        return new DashboardPage(driver);
    }
    
    /**
     * Check if error message is displayed
     */
    public boolean isErrorMessageDisplayed() {
        try {
            return errorMessage.isDisplayed();
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Get error message text
     */
    public String getErrorMessage() {
        if (isErrorMessageDisplayed()) {
            return errorMessage.getText();
        }
        return "";
    }
    
    /**
     * Get page title
     */
    public String getPageTitle() {
        return pageTitle.getText();
    }
    
    /**
     * Check if on login page
     */
    public boolean isOnLoginPage() {
        return driver.getCurrentUrl().contains("/login");
    }
}