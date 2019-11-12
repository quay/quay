import { element, by, browser, $, ElementFinder, ExpectedConditions as until } from 'protractor';


export class ManageTriggerViewObject {

  public sections: {[name: string]: ElementFinder} = {
    namespace:          $('linear-workflow-section[section-id=namespace]'),
    githostrepo:        $('linear-workflow-section[section-id=repo][section-title="Select Repository"]'),
    customrepo:         $('linear-workflow-section[section-id=repo][section-title="Git Repository"]'),
    triggeroptions:     $('linear-workflow-section[section-id=triggeroptions]'),
    dockerfilelocation: $('linear-workflow-section[section-id=dockerfilelocation]'),
    contextlocation:    $('linear-workflow-section[section-id=contextlocation]'),
    robot:              $('linear-workflow-section[section-id=robot]'),
    verification:       $('linear-workflow-section[section-id=verification]'),
  };

  private customGitRepoInput: ElementFinder = element(by.model('$ctrl.buildSource'));
  private dockerfileLocationInput: ElementFinder = this.sections['dockerfilelocation'].$('input');
  private dockerfileLocationDropdownButton: ElementFinder = this.sections['dockerfilelocation']
                                                              .$('button[data-toggle=dropdown');
  private dockerContextInput: ElementFinder = this.sections['contextlocation'].$('input');
  private dockerContextDropdownButton: ElementFinder = this.sections['contextlocation']
                                                         .$('button[data-toggle=dropdown');
  private robotAccountOptions: ElementFinder = this.sections['robot']
                                                 .element(by.repeater('$ctrl.orderedData.visibleEntries'));

  public continue() {
    return element(by.buttonText('Continue')).click();
  }

  public enterRepositoryURL(url: string) {
    browser.wait(until.presenceOf(this.customGitRepoInput));
    this.customGitRepoInput.clear();

    return this.customGitRepoInput.sendKeys(url);
  }

  public enterDockerfileLocation(path: string) {
    browser.wait(until.presenceOf(this.dockerfileLocationInput));
    this.dockerfileLocationInput.clear();

    return this.dockerfileLocationInput.sendKeys(path);
  }

  public getDockerfileSuggestions() {
    return this.dockerfileLocationDropdownButton.click()
      .then<string[]>(() => element.all(by.repeater('$ctrl.paths')).map(result => result.getText()));
  }

  public enterDockerContext(path: string) {
    browser.wait(until.presenceOf(this.dockerContextInput));
    this.dockerContextInput.clear();

    return this.dockerContextInput.sendKeys(path);
  }

  public getDockerContextSuggestions() {
    return this.dockerContextDropdownButton.click()
      .then<string[]>(() => element.all(by.repeater('$ctrl.contexts')).map(result => result.getText()));
  }

  public selectRobotAccount(index: number) {
    return element.all(by.css('input[type=radio]')).get(index).click();
  }
}
