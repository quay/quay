import { $, browser, ExpectedConditions as until, by, element } from 'protractor';

export const nameInput = $('#signin-username');
export const passwordInput = $('#signin-password');
export const submitButton = element(by.partialButtonText('Sign in to'));
export const logOutLink = element(by.linkText('Sign out all sessions'));
export const userDropdown = $('.dropdown-toggle.user-dropdown.user-view');

export const login = async(username: string, password: string) => {
  await browser.wait(until.visibilityOf(nameInput));
  await nameInput.sendKeys(username);
  await passwordInput.sendKeys(password);
  await submitButton.click();
  await browser.wait(until.presenceOf(userDropdown));
};

export const logout = async() => {
  await browser.wait(until.presenceOf(userDropdown));
  await userDropdown.click();
  await browser.wait(until.presenceOf(logOutLink));
  await logOutLink.click();
  await browser.wait(until.presenceOf($('.user-view')));
};
