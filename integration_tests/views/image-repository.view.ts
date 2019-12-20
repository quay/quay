import { $, browser, ExpectedConditions as until, by, element } from 'protractor';
import { appHost, testName, userName } from '../protractor.conf';

export const createrepoButton = element(by.linkText('Create New Repository'));
export const reponameInput = $('#repoName');
export const publicrepoClick = $('#publicrepo');
export const privaterepoClick = $('#privaterepo');
export const publicrepoButton = element(by.partialButtonText('Create Public Repository'));
export const privaterepoButton = element(by.partialButtonText('Create Private Repository'));

export const addtagButton = element(by.linkText('Add New Tag'));
export const tagInput = element.all(by.model('tagToCreate')).get(0);
export const createtagButton = element(by.partialButtonText('Create Tag'));

export const movetagButton = element(by.partialButtonText('Move Tag'));

export const restoretagButton = element(by.partialButtonText('Restore Tag'));

export const deletetagButton = element(by.linkText('Delete Tag'));
export const deletetagClick = element.all(by.partialButtonText('Delete Tag')).get(1);

export const deleterepoButton = element(by.css('.delete-btn'));
export const deleterepoClick = element.all(by.buttonText('Delete')).get(1);

export const tags = element(by.xpath("//span[@bo-text='tag.name']"));

export const createrepo = async(reponame: string, type: number) => {
  await browser.wait(until.presenceOf(createrepoButton));
  await createrepoButton.click();
  await browser.wait(until.visibilityOf(reponameInput));
  await reponameInput.sendKeys(reponame);
  if (type == 1) {
    await publicrepoClick.click();
    await browser.wait(until.presenceOf(publicrepoButton));
    await publicrepoButton.click();
  } else {
    await privaterepoClick.click();
    await browser.wait(until.presenceOf(privaterepoButton));
    await privaterepoButton.click();
  }
};

export const addnewtag = async(previoustag: string, newtag: string) => {
//  const optionsDropdown = element(by.xpath("//span[@bo-text=tag.name and text()='"+previoustag+"']/ancestor::tbody//i[@data-title=Options]"));
  const optionsDropdown = element(by.xpath("/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[3]/span/div/div/cor-tab-panel/div/div/div/cor-tab-pane[2]/div/div/div/div[1]/table/tbody/tr/td[8]/span/span/div/i"));


  await browser.wait(until.presenceOf(optionsDropdown));
  await optionsDropdown.click();
  await browser.wait(until.presenceOf(addtagButton));
  await addtagButton.click();
  await browser.wait(until.visibilityOf(tagInput), 5000);
  console.log(tagInput.getAttribute('class'));
  await tagInput.sendKeys(newtag); //always meet javascript error: a.tagName.toUpperCase is not a function
  await createtagButton.click();
};

export const movetag = async(previoustag: string, newtag: string) => {
  const optionsDropdown = element(by.xpath("//span[@bo-text='tag.name' and text()='"+previoustag+"']/ancestor::tbody//i[@data-title='Options']"));

  await browser.wait(until.presenceOf(optionsDropdown));
  await optionsDropdown.click();
  await browser.wait(until.presenceOf(addtagButton));
  await addtagButton.click();
  await browser.wait(until.visibilityOf(tagnameInput));
  await tagnameInput.sendKeys(newtag);
  await movetagButton.click();
};

export const reverttag = async(tagname: string) => {
  const reverttagButton = $(`Revert [data-title=${tagname}]`);

  await browser.wait(until.presenceOf(reverttagButton));
  await reverttagButton.click();
  await browser.wait(until.presenceOf(restoretagButton));
  await restoretagButton.click();
};

export const deletetag = async(tagname: string) => {
  const optionsDropdown = element(by.xpath("/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[3]/span/div/div/cor-tab-panel/div/div/div/cor-tab-pane[2]/div/div/div/div[1]/table/tbody/tr/td[8]/span/span/div/i"));
  await browser.wait(until.presenceOf(optionsDropdown));
  await optionsDropdown.click();
  await browser.wait(until.presenceOf(deletetagButton));
  await deletetagButton.click();
  await browser.wait(until.visibilityOf(deletetagClick), 5000);
  await deletetagClick.click();
};

export const deleterepo = async(reponame: string) => {
  await browser.wait(until.presenceOf(deleterepoButton));
  await deleterepoButton.click();
  await browser.wait(until.visibilityOf(deleterepoClick), 5000);
  await deleterepoClick.click();
};

