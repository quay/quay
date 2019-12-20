import { browser, ExpectedConditions as until, $, $$ } from 'protractor';
import { appHost, registryHost, testName, userName, userPasswd } from '../protractor.conf';
import * as loginView from '../views/quay-login.view';
import * as createrepoView from '../views/image-repository.view';
import {execSync} from 'child_process';

const BROWSER_TIMEOUT = 15000;

describe('Create an image repository', () => {
  it(`create image repository ${testName} if necessary`, async() => {
    await createrepoView.createrepo(testName, 1);
    await browser.sleep(1000);
    expect(browser.getCurrentUrl()).toContain(testName);
  });
});

describe('Push/pull images to/from Quay via podman', () => {
  it(`push image to repository ${testName}`, async() => {
    execSync(`sudo podman pull docker.io/busybox`);
    execSync(`sudo podman tag docker.io/busybox ${registryHost}/${userName}/${testName}:busybox`);
    execSync(`sudo podman push --tls-verify=false --creds=${userName}:${userPasswd} ${registryHost}/${userName}/${testName}:busybox`);
    await browser.get(`${appHost}/repository/${userName}/${testName}?tab=tags`);
    await browser.sleep(1000);
    expect(createrepoView.tags.getText()).toBe('busybox');
  });

  it(`pull image to repository ${testName}`, async() => {
    execSync(`sudo podman rmi ${registryHost}/${userName}/${testName}:busybox`);
    execSync(`sudo podman pull --tls-verify=false ${registryHost}/${userName}/${testName}:busybox`);
  });
});

describe('Viewing and modifying tags', () => {
  beforeAll(async() => {
    await browser.get(`${appHost}/repository/${userName}/${testName}?tab=tags`);
    await browser.sleep(1000);
  });

/*  it('add new tag for image manifest', async() => {
    await createrepoView.addnewtag('busybox', 'testtag1');
    expect(browser.wait(ExpectedConditions.textToBePresentInElement('testtag1'), 5000));
  });

  it('move to existing tag for image manifest', async() => {
    execSync(`sudo podman pull docker.io/openshift/hello-openshift`);
    execSync(`sudo podman tag docker.io/openshift/hello-openshift ${registryHost}/${userName}/${testName}:hello`);
    execSync(`sudo podman push --tls-verify=false --creds=${userName}:${userPasswd} ${registryHost}/${userName}/${testName}:hello`);
    expect(browser.wait(ExpectedConditions.textToBePresentInElement('hello'), 5000));
    await createrepoView.movetag('busybox', 'hello');
    // add an expect step to check moving tag success
  });

  it('revert the tag to previous image manifest', async() => {
    await browser.get(`${appHost}/repository/${userName}/${testName}?tab=history`);
    await browser.sleep(1000);
    await createrepoView.reverttag('hello');
    // add an expect step to check tag revert
  });
*/
  it('delete a tag', async() => {
    await browser.get(`${appHost}/repository/${userName}/${testName}?tab=tags`);
    await browser.sleep(1000);
    await createrepoView.deletetag('buybox');
    // expectation step
    const pullerr = async() => {
      return execSync(`sudo podman pull --tls-verify=false ${registryHost}/${userName}/${testName}:busybox`).toString
    };
    expect(pullerr()).toBe('Failed');
  });
});

describe('Delete image repository', () => {
  beforeAll(async() => {
    await browser.get(`${appHost}/repository/${userName}/${testName}?tab=settings`);
    await browser.sleep(1000);
  });
  it(`delete image repository ${testName}`, async() => {
    await createrepoView.deleterepo(`${testName}`);
    await browser.get(`${appHost}/repository/${userName}/${testName}`);
  });
});

