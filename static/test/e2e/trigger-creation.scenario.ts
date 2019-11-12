import { browser, element, by, $, $$ } from 'protractor';
import { ManageTriggerViewObject } from '../../js/directives/ui/manage-trigger/manage-trigger.view-object';
import { appHost } from '../protractor.conf';


describe("Trigger Creation", () => {
  const username = 'devtable';
  const password = 'password';
  var manageTriggerView: ManageTriggerViewObject = new ManageTriggerViewObject();

  beforeAll((done) => {
    browser.waitForAngularEnabled(false);

    // Sign in
    browser.get(appHost);
    $$('a[href="/signin/"]').get(1).click();
    $('#signin-username').sendKeys(username);
    $('#signin-password').sendKeys(password);
    element(by.partialButtonText('Sign in')).click();
    browser.sleep(4000).then(() => done());
  });

  afterAll(() => {
    browser.waitForAngularEnabled(true);
  });

  describe("for custom git", () => {

    beforeAll(() => {
      // Navigate to trigger setup
      browser.get(`${appHost}/repository/devtable/simple?tab=builds`)
    });

    it("can select custom git repository push as a trigger option", (done) => {
      element(by.buttonText('Create Build Trigger')).click();
      element(by.linkText('Custom Git Repository Push')).click();
      browser.sleep(1000);
      done();
    });

    it("shows custom git repository section first", () => {
      expect(manageTriggerView.sections['customrepo'].isDisplayed()).toBe(true);
    });

    it("does not accept invalid custom git repository URL's", () => {
      manageTriggerView.continue()
        .then(() => fail('Should not accept empty input for repository URL'))
        .catch(() => manageTriggerView.enterRepositoryURL('git@some'))
        .then(() => manageTriggerView.continue())
        .then(() => fail('Should not accept invalid input for repository URL'))
        .catch(() => null);
    });

    it("proceeds to Dockerfile location section when given valid URL", () => {
      manageTriggerView.enterRepositoryURL('git@somegit.com:someuser/somerepo.git');
      manageTriggerView.continue()
        .then(() => {
          expect(manageTriggerView.sections['dockerfilelocation'].isDisplayed()).toBe(true);
        })
        .catch(reason => fail(reason));
    });

    it("does not accept Dockerfile location that does not end with a filename", () => {
      manageTriggerView.enterDockerfileLocation('/')
        .then(() => manageTriggerView.continue())
        .then(() => fail('Should not accept Dockerfile location that does not end with a filename'))
        .catch(() => null);
    });

    it("does not provide Dockerfile location suggestions", () => {
      manageTriggerView.getDockerfileSuggestions()
        .then((results) => {
          expect(results.length).toEqual(0);
        });
    });

    it("proceeds to Docker context location section when given a valid Dockerfile location", () => {
      manageTriggerView.enterDockerfileLocation('/Dockerfile')
        .then(() => manageTriggerView.continue())
        .then(() => {
          expect(manageTriggerView.sections['contextlocation'].isDisplayed()).toBe(true);
        })
        .catch(reason => fail(reason));
    });

    it("does not accept invalid Docker context", () => {
      manageTriggerView.enterDockerContext('')
        .then(() => manageTriggerView.continue())
        .then(() => fail('Should not acccept invalid Docker context location'))
        .catch(() => null);
    });

    it("provides suggestions for Docker context based on Dockerfile location", () => {
      manageTriggerView.getDockerContextSuggestions()
        .then((results) => {
          expect(results).toContain('/');
        });
    });

    it("proceeds to robot selection section when given valid Docker context", () => {
      manageTriggerView.enterDockerContext('/')
        .then(() => manageTriggerView.continue())
        .then(() => {
          expect(manageTriggerView.sections['robot'].isDisplayed()).toBe(true);
        })
        .catch(reason => fail(reason));
    });

    it("allows selection of optional robot account", () => {
      manageTriggerView.selectRobotAccount(0)
        .catch(reason => fail(reason));
    });

    it("proceeds to verification section", () => {
      manageTriggerView.continue()
        .then(() => {
          expect(manageTriggerView.sections['verification'].isDisplayed()).toBe(true);
        })
        .catch(reason => fail(reason));
    });

    it("displays success message after creating the trigger", () => {
      manageTriggerView.continue()
        .then(() => {
          browser.sleep(2000);
          expect($('h3').getText()).toEqual('Trigger has been successfully activated');
        })
        .catch(reason => fail(reason));
    });
  });

  describe("for githost", () => {

    beforeAll(() => {
      // Navigate to trigger setup
      browser.get(`${appHost}/repository/devtable/simple?tab=builds`);
    });

    it("can select GitHub repository push as a trigger option", () => {
      element(by.partialButtonText('Create Build Trigger')).click();
      element(by.linkText('GitHub Repository Push')).click();
    });

    it("redirects to GitHub login page for granting authentication", () => {
      expect(browser.getCurrentUrl()).toContain('github.com');

      // TODO: Which credentials do we use to login to GitHub?
    });

    xit("shows namespace select section first", () => {
      expect(manageTriggerView.sections['namespace'].isDisplayed()).toBe(true);
    });
  });
});
