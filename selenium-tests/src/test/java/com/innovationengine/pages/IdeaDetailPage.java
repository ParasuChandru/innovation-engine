package com.innovationengine.pages;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

/**
 * Page Object Model for Idea Detail Page
 * Innovation Engine Application
 */
public class IdeaDetailPage {
    
    private WebDriver driver;
    private WebDriverWait wait;
    
    // Page Elements
    @FindBy(css = "h1")
    private WebElement ideaTitle;
    
    @FindBy(xpath = "//span[contains(@class, 'rounded-full')]")
    private WebElement statusBadge;
    
    @FindBy(xpath = "//a[contains(text(), 'Back')]")
    private WebElement backButton;
    
    /**
     * Constructor
     */
    public IdeaDetailPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        PageFactory.initElements(driver, this);
    }
    
    /**
     * Get idea title
     */
    public String getIdeaTitle() {
        return ideaTitle.getText();
    }
    
    /**
     * Get idea status
     */
    public String getStatus() {
        return statusBadge.getText();
    }
    
    /**
     * Check if on idea detail page
     */
    public boolean isOnIdeaDetailPage() {
        return driver.getCurrentUrl().contains("/ideas/");
    }
    
    /**
     * Get idea ID from URL
     */
    public String getIdeaIdFromUrl() {
        String url = driver.getCurrentUrl();
        String[] parts = url.split("/ideas/");
        if (parts.length > 1) {
            return parts[1].split("/")[0];
        }
        return "";
    }
}